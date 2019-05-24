import importlib

import numpy as np
import pandas as pd

import pandas.api.types as ptypes

import petk.constants as constants


def get_description(series, nulls=constants.NULLS, name=''):
    '''
    Profile a single data column

    Parameters:
    columns (str): Identify the column to profile

    Returns:
    (DataFrame): Profile result
    '''

    count = series[~series.isin(nulls)].count() # ONLY non-NaN observations
    dtype = get_type(series)

    description = {
        'content_type': dtype,
        'memory_usage': series.memory_usage(),
        'count': count,
        'p_null': (series.size - count) / series.size,
        'n_null': series.size - count,
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

    return pd.DataFrame(pd.Series(description, name=name))

def get_point_location(point, provider='nominatim', user_agent='petk'):
    if importlib.util.find_spec('geopy') is not None:
        from geopandas.tools import reverse_geocode
        from shapely.geometry import MultiPoint

        loc = reverse_geocode(point.centroid, provider=provider, user_agent=user_agent)['address'][0]
        return ', '.join(loc.split(', ')[1:])

def get_type(series):
    if series.name == 'geometry':
        # TODO: THIS HAS TO BE BETTER
        return constants.TYPE_GEO

    try:
        distinct_count = series.nunique()
        value_count = series.nunique(dropna=False)

        modifier = ''
        if value_count == 1 and distinct_count == 0:
            modifier = constants.TYPE_EMPTY
        elif distinct_count == 1:
            modifier = constants.TYPE_CONST
        elif value_count == len(series):
            modifier = constants.TYPE_UNIQUE

        dtype = get_dtype(series)

        return ' '.join([modifier, dtype]).strip()
    except:
        # eg. 2D series
        return constants.TYPE_UNSUPPORTED

def get_dtype(data):
    if ptypes.is_bool_dtype(data) or (isinstance(data, pd.Series) and data.nunique() == 2 and pd.api.types.is_numeric_dtype(data)):
        return constants.TYPE_BOOL
    elif ptypes.is_datetime64_dtype(data):
        return constants.TYPE_DATE
    elif ptypes.is_numeric_dtype(data):
        return constants.TYPE_NUM
    else:
        return constants.TYPE_STR

def is_outbound(x, lower, upper):
    if lower and x < lower:
        return 'Value is less than the lower bound'
    elif upper and x > upper:
        return 'Value is greater than the upper bound'

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
