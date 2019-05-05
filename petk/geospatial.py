# Validation methods deals with the GeoDataFrame content as a whole

def validate_single_geom_type(data):
    geom_types = data.geom_type.unique()

    return len(geom_types) == 1

def validate_crs(self):
    pass
