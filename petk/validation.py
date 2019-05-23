from shapely.validation import explain_validity

import petk.constants as constants
import petk.tools as tools

# TODO: assert kwargs are given

def bounding_box(serie, **kwargs):
    xmin, xmax, ymin, ymax = kwargs.get('bounding_box')

    outsiders = serie.loc[~serie.index.isin(serie.cx[xmin:xmax, ymin:ymax].index)]

    if not outsiders.empty:
        return outsiders.apply(lambda x: 'Geometry outside of bbox({0}, {1}, {2}, {3})'.format(xmin, xmax, ymin, ymax))

def geospatial(series):
    invalids = series[~series.is_valid]

    if not invalids.empty:
        return invalids.apply(lambda x: explain_validity(x) if not x is None else 'Null geometry')

def range(series, **kwargs):
    dtype = tools.get_type(series)

    if dtype in [constants.TYPE_DATE, constants.TYPE_NUM]:
        lower, upper = kwargs.get('range')

        outbounds = series.apply(tools.is_outbound, args=[lower, upper])
        outbounds = outbounds[~outbounds.isnull()]

        if not outbounds.empty:
            return outbounds
    elif dtype == constants.TYPE_STR:
        accepted = kwargs.get('range')

        outbounds = series[~series.isin(kwargs.get('accepted'))]

        if not outbounds.empty:
            return outbounds.apply(lambda x: 'Value not within the accepted range')

def sliver(series, **kwargs):
    projection = kwargs.get('projected_coordinates')
    threshold = kwargs.get('sliver_threshold')

    pieces = series.explode().to_crs({'init': 'epsg:{0}'.format(projection), 'units': 'm'})

    slivers = pieces.apply(tools.is_sliver, args=[threshold])
    slivers = slivers[slivers].groupby(level=0).count()

    if not slivers.empty:
        return slivers.apply(lambda x: '{0} slivers found within geometry'.format(x))

def type(series, **kwargs):
    pass
