from shapely.validation import explain_validity

import petk.constants as constants
import petk.tools as tools

# TODO: assert kwargs are given

def bounding_box(serie, bounding_box):
    xmin, xmax, ymin, ymax = bounding_box

    outsiders = serie.loc[~serie.index.isin(serie.cx[xmin:xmax, ymin:ymax].index)]

    if not outsiders.empty:
        return outsiders.apply(lambda x: 'Geometry outside of bbox({0}, {1}, {2}, {3})'.format(xmin, xmax, ymin, ymax))

def geospatial(series):
    invalids = series[~series.is_valid]

    if not invalids.empty:
        return invalids.apply(lambda x: explain_validity(x) if not x is None else 'Null geometry')

def range(series, range):
    dtype = tools.get_type(series)
    print(series.name, dtype)

    if any(dtype in type for type in [constants.TYPE_DATE, constants.TYPE_NUM]):
        lower, upper = range

        outbounds = series.apply(tools.is_outbound, args=[lower, upper])
        outbounds = outbounds[~outbounds.isnull()]

        if not outbounds.empty:
            return outbounds
    elif dtype in constants.TYPE_STR:
        outbounds = series[~series.isin(range)]

        if not outbounds.empty:
            return outbounds.apply(lambda x: 'Value not within the accepted range')

def sliver(series, params):
    pieces = series.explode().to_crs({'init': 'epsg:{0}'.format(params['projected_coordinates']), 'units': 'm'})

    slivers = pieces.apply(tools.is_sliver, args=[params['threshold']])
    slivers = slivers[slivers].groupby(level=0).count()

    if not slivers.empty:
        return slivers.apply(lambda x: '{0} slivers found within geometry'.format(x))

def content_type(series, dtype):
    dtypes = series.apply(lambda x: tools.get_dtype([x]))
    expected = tools.get_dtype(dtype)

    invalids = dtypes[dtypes != expected]

    if not invalids.empty:
        return invalids.apply(lambda x: 'Expected type {0} found type {1}'.format(expected, x))
