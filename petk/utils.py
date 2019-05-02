import numpy as np
import pandas as pd

import pandas.api.types as ptypes

import petk.constants as constants


def get_type(array):
    try:
        distinct_count = array.nunique()
        value_count = array.nunique(dropna=False)

        # TODO: GEOMETRY

        if value_count == 1 and distinct_count == 0:
            return constants.TYPE_EMPTY
        elif distinct_count == 1:
            return constants.TYPE_CONST
        elif ptypes.is_bool_dtype(array) or (distinct_count == 2 and pd.api.types.is_numeric_dtype(array)):
            return constants.TYPE_BOOL
        elif ptypes.is_datetime64_dtype(array):
            return constants.TYPE_DATE
        elif ptypes.is_numeric_dtype(array):
            return constants.TYPE_NUM
        elif value_count == len(array):
            return constants.TYPE_UNIQUE
        else:
            return constants.TYPE_STR
    except:
        # eg. 2D arrays
        return constants.TYPE_UNSUPPORTED
