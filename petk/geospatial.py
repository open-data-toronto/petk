from shapely.validation import explain_validity

import geopandas as gpd

import petk.constants as constants


# Validation methods deals with the GeoDataFrame content as a whole


def validate_single_geom_type(df):
    geom_types = df.geom_type.unique()

    return len(geom_types) == 1

def validate_crs(self):
    pass

# Find methods deals with records

def find_invalids(data):
    invalid = pd.DataFrame(data[~data.is_valid])

    if not invalid.empty:
        invalid['reason'] = invalid['geometry'].apply(lambda x: explain_validity(x) if not x is None else 'Null geometry')
        return invalid

def find_outsiders(data, bbox=[], xmin=None, xmax=None, ymin=None, ymax=None):
    assert len(bbox) == 4 or all(var is not None for var in [xmin, xmax, ymin, ymax]), 'Invalid bounding box'

    if len(bbox) == 4:
        xmin, xmax, ymin, ymax = bbox

    # There has to be a better way to select outside of a bounding box...
    invalid = pd.GeoDataFrame(data.loc[~data.index.isin(data.cx[xmin:xmax, ymin:ymax].index)])
    invalid['notes'] = 'Outside of bbox({0}, {1}, {2}, {3})'.format(xmin, xmax, ymin, ymax)

    if not invalid.empty:
        return invalid

def find_slivers(data, area_thresh=constants.SLIVER_AREA, line_thresh=constants.SLIVER_LINE):
    pieces = data.explode().to_crs({'init': 'epsg:2019', 'units': 'm'})

    slivers = pieces.apply(_find_sliver, args=(area_thresh, line_thresh))
    slivers = slivers[slivers].groupby(level=0).count()

    if not slivers.empty:
        slivers = gpd.GeoDataFrame({
            'geometry': data,
            'notes': slivers.apply(lambda x: '{0} slivers found within geometry'.format(x))
        }).dropna()

        return slivers

def _find_sliver(x, area_thresh, line_thresh):
    if 'polygon' in x.geom_type.lower():
        return x.area < area_thresh
    elif 'linestring' in x.geom_type.lower():
        return x.length < line_thresh
    else:   # Points
        return False
