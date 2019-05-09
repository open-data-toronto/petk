from shapely.validation import explain_validity

import importlib

import numpy as np
import pandas as pd

import pandas.api.types as ptypes

import petk.constants as constants


def get_description(series, name=''):
    '''
    Profile a single data column

    Parameters:
    columns (str): Identify the column to profile

    Returns:
    (OrderedDict): Profile result
    '''

    count = series.count() # ONLY non-NaN observations
    dtype = get_type(series)

    description = {
        'type': dtype,
        'column': series.name,
        'memory_usage': series.memory_usage(),
        'count': count,
        'p_missing': (series.size - count) / series.size,
        'n_missing': series.size - count,
    }

    if not dtype in [constants.TYPE_UNSUPPORTED, constants.TYPE_CONST, constants.TYPE_UNIQUE, constants.TYPE_GEO]:
        n_distinct = series.nunique()

        description.update({
            'distinct_count': n_distinct,
            'is_unique': n_distinct == series.size,
            'p_unique': n_distinct * 1.0 / series.size
        })

        if dtype == constants.TYPE_BOOL:
            description.update({
                'mean': series.mean()
            })
        elif dtype in [constants.TYPE_DATE, constants.TYPE_NUM]:
            n_inf = series.loc[(~np.isfinite(series)) & series.notnull()].size

            description.update({
                'p_infinite': n_inf / series.size,
                'n_infinite': n_inf,
                'min': series.min(),
                'max': series.max()
            })

            for perc in [0.05, 0.25, 0.5, 0.75, 0.95]:
                description['{:.0%}'.format(perc)] = series.quantile(perc)

            if dtype == constants.TYPE_NUM:
                n_zeros = series.size - np.count_nonzero(series)

                description.update({
                    'mean': series.mean(),
                    'std': series.std(),
                    'variance': series.var(),
                    'iqr': series.quantile(0.75) - series.quantile(0.25),
                    'kurtosis': series.kurt(),
                    'skewness': series.skew(),
                    'sum': series.sum(),
                    'mad': series.mad(),
                    'cv': series.std() / series.mean(),
                    'n_zeros': n_zeros,
                    'p_zeros': n_zeros / series.size
                })

    # OrderedDict used to fixed the DataFrame column orders
    return pd.DataFrame(pd.Series(description, name=name))

def get_invalids(data):
    '''
    Find the invalid geometries within the data

    Returns:
    (DataFrame): Invalid geometries and the reason
    '''

    invalids = data[~data.is_valid]

    if not invalids.empty:
        return invalids['geometry'].apply(lambda x: explain_validity(x) if not x is None else 'Null geometry')

def get_outsiders(data, xmin, xmax, ymin, ymax):
    '''
    Find the geometries outside of a certain bounding box

    Parameters:
    xmin (numeric): Min X of the bounding box
    xmax (numeric): Max X of the bounding box
    ymin (numeric): Min Y of the bounding box
    ymax (numeric): Max Y of the bounding box

    Returns:
    (DataFrame): Out of bound geometries
    '''

    assert xmin < xmax and ymin < ymax, 'Invalid bounding box'

    # TODO: There has to be a better way to select outside of a bounding box...
    outsiders = data.loc[~data.index.isin(data.cx[xmin:xmax, ymin:ymax].index)]

    if not outsiders.empty:
        return outsiders['geometry'].apply(lambda x: 'Geometry outside of bbox({0}, {1}, {2}, {3})'.format(xmin, xmax, ymin, ymax))

def get_slivers(data, projection=None, area_thresh=constants.SLIVER_AREA, length_thresh=constants.SLIVER_LINE):
    '''
    Find the slivers within the geometries

    Parameters:
    projection    (numeric): EPSG number for the geometry of the data
    area_thresh   (numeric): Threshold area for a Polygon to be considered a sliver
    length_thresh (numeric): Threshold length for a Line to be considered a sliver

    Returns:
    (DataFrame): Sliver geometries
    '''

    assert projection, 'Projection required'

    def is_sliver(x, area_thresh, length_thresh):
        if 'polygon' in x.geom_type.lower():
            return x.area < area_thresh
        elif 'linestring' in x.geom_type.lower():
            return x.length < length_thresh
        else:   # Points
            return False

    pieces = data.explode().to_crs({'init': 'epsg:{0}'.format(projection), 'units': 'm'})

    slivers = pieces['geometry'].apply(is_sliver, args=(area_thresh, length_thresh))
    slivers = slivers[slivers].groupby(level=0).count()

    if not slivers.empty:
        return slivers.apply(lambda x: '{0} slivers found within geometry'.format(x))

# def get_frequent_values(self, top):
#     return series.value_counts(dropna=False).head(top)
#
# def get_distribution(self, top):
#     assert dtype in [constants.STR, constants.DATE, constants.NUM], 'Distribution not available'
#
#     if dtype == constants.STR:
#         # Histogram of most frequen top values
#         pass
#     else:
#         # Distribution Plot
#         pass

def get_point_location(point, provider='nominatim', user_agent='petk'):
    if importlib.util.find_spec('geopy') is not None:
        from geopandas.tools import reverse_geocode
        from shapely.geometry import MultiPoint

        loc = reverse_geocode(point.centroid, provider=provider, user_agent=user_agent)['address'][0]
        return ', '.join(loc.split(', ')[1:])

def get_type(series):
    if series.name == 'geometry':
        return constants.TYPE_GEO

    try:
        distinct_count = series.nunique()
        value_count = series.nunique(dropna=False)

        if value_count == 1 and distinct_count == 0:
            return constants.TYPE_EMPTY
        elif distinct_count == 1:
            return constants.TYPE_CONST
        elif ptypes.is_bool_dtype(series) or (distinct_count == 2 and pd.api.types.is_numeric_dtype(series)):
            return constants.TYPE_BOOL
        elif ptypes.is_datetime64_dtype(series):
            return constants.TYPE_DATE
        elif ptypes.is_numeric_dtype(series):
            return constants.TYPE_NUM
        elif value_count == len(series):
            return constants.TYPE_UNIQUE
        else:
            return constants.TYPE_STR
    except:
        # eg. 2D series
        return constants.TYPE_UNSUPPORTED
