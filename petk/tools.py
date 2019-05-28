from shapely.geometry import mapping, MultiPoint

import importlib

import numpy as np
import pandas as pd
import geopandas as gpd

import pandas.api.types as pd_types

import petk.constants as constants


def get_description(series, name=''):
    count = count = series.count() # ONLY non-NaN observations
    dtype = get_type(series)

    description = {
        'content_type': dtype,
        'memory_usage': series.memory_usage(),
        'count': count,
        'p_null': (series.size - count) / series.size,
        'n_null': series.size - count,
    }

    # TODO: if GEO calculate other things
    if not dtype in [constants.TYPE_UNSUPPORTED, constants.TYPE_GEO]:
        n_distinct = series.nunique()

        description.update({
            'distinct_count': n_distinct,
            'is_constant': n_distinct == 1,
            'is_unique': n_distinct == series.size,
            'p_unique': n_distinct * 1.0 / series.size
        })

        if dtype == constants.TYPE_BOOL:
            description.update({
                'mean': series.mean()
            })
        elif dtype in [constants.TYPE_DATE, constants.TYPE_NUM]:
            description.update({
                'min': series.min(),
                'max': series.max()
            })

            for perc in [0.05, 0.25, 0.5, 0.75, 0.95]:
                description['{:.0%}'.format(perc)] = series.quantile(perc)

            if dtype == constants.TYPE_NUM:
                n_zeros = series.size - np.count_nonzero(series)
                n_inf = series.loc[(~np.isfinite(series)) & series.notnull()].size

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
                    'p_infinite': n_inf / series.size,
                    'n_infinite': n_inf,
                    'n_zeros': n_zeros,
                    'p_zeros': n_zeros / series.size
                })

    return pd.Series(description, name=name).to_frame()

def get_point_location(points, provider='nominatim', user_agent='petk'):
    centroid = MultiPoint(points).centroid

    if importlib.util.find_spec('geopy') is not None:
        from geopandas.tools import reverse_geocode

        return reverse_geocode(centroid, provider=provider, user_agent=user_agent)['address'][0]
    else:
        return ', '.join([str(x) for x in mapping(centroid)['coordinates']])

def get_type(series):
    if series.name == 'geometry' and isinstance(series, gpd.GeoSeries):
        return constants.TYPE_GEO

    try:
        distinct_count = series.nunique()
        value_count = series.nunique(dropna=False)

        if value_count == 1 and distinct_count == 0:
            return constants.TYPE_EMPTY
        elif pd_types.is_bool_dtype(series):
            return constants.TYPE_BOOL
        elif pd_types.is_datetime64_dtype(series):
            return constants.TYPE_DATE
        elif pd_types.is_numeric_dtype(series):
            return constants.TYPE_NUM
        else:
            return constants.TYPE_STR
    except:
        # eg. 2D series
        return constants.TYPE_UNSUPPORTED

def is_outbound(x, lower, upper):
    if lower and x < lower:
        return 'Value is less than the lower bound'
    elif upper and x > upper:
        return 'Value is greater than the upper bound'
    else:
        return None

def is_sliver(x, threshold):
    if 'polygon' in x.geom_type.lower():
        return x.area < threshold
    elif 'linestring' in x.geom_type.lower():
        return x.length < threshold
    else:   # Points
        return False

def key_exists(content, *keys):
    _values = content

    for k in keys:
        try:
            _values = _values[k]
        except KeyError:
            return False

    return True
