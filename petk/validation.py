from shapely.validation import explain_validity

import pandas as pd

import petk.constants as constants
import petk.tools as tools

# TODO: assert kwargs are given
# TODO: catch cases when partial requirements are given

def bounding_box(series, bounding_box):
    xmin, xmax, ymin, ymax = bounding_box

    assert xmin < xmax and ymin < ymax, 'Invalid bounding box given'

    outsiders = series.loc[~series.index.isin(series.cx[xmin:xmax, ymin:ymax].index)]

    if not outsiders.empty:
        return outsiders.apply(lambda x: 'Geometry outside of bbox({0}, {1}, {2}, {3})'.format(xmin, xmax, ymin, ymax))

# def content_type(series, expected):
    # dtypes = series.apply(lambda x: tools.get_type(pd.Series([x], name=series.name)))
    # expected = tools.get_simple_type(expected)
    #
    # invalids = dtypes[dtypes != expected]
    #
    # if not invalids.empty:
    #     return invalids.apply(lambda x: 'Expected type {0} found type {1}'.format(expected, x))

def geospatial(series):
    invalids = series[~series.is_valid]

    if not invalids.empty:
        return invalids.apply(lambda x: explain_validity(x) if not x is None else 'Null geometry')

def min(series, lim):
    outbounds = series[series < lim]

    if not outbounds.empty:
        return outbounds.apply(lambda x: 'Value is less than lower bound')

def max(series, lim):
    outbounds = series[series > lim]

    if not outbounds.empty:
        return outbounds.apply(lambda x: 'Value is greater than upper bound')

def sliver(series, params):
    pieces = series.explode().to_crs({'init': 'epsg:{0}'.format(params['projected_coordinates']), 'units': 'm'})

    slivers = pieces.apply(tools.is_sliver, args=[params['threshold']])
    slivers = slivers[slivers].groupby(level=0).count()

    if not slivers.empty:
        return slivers.apply(lambda x: '{0} slivers found within geometry'.format(x))
