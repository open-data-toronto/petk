import numpy as np
import pandas as pd

import pandas.api.types as ptypes

import petk.constants as constants


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
