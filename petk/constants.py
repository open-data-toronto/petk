import numpy as np

TYPE_BOOL = 'BOOLEAN'
TYPE_DATE = 'DATE'
TYPE_GEO = 'GEOMETRY'
TYPE_NUM = 'NUMERIC'
TYPE_STR = 'STRING'

TYPE_EMPTY = 'EMPTY'
TYPE_UNSUPPORTED = 'UNSUPPORTED'

SCHEMA_STRUCTURE = {
    'nulls': {
        'to_list': True,
        'types': [TYPE_BOOL, TYPE_DATE, TYPE_GEO, TYPE_NUM, TYPE_STR],
        'defaults': [None, np.nan, 'null', '']
    },
    'default': {
        'to_list': False,
        'types': [TYPE_BOOL, TYPE_DATE, TYPE_GEO, TYPE_NUM, TYPE_STR]
    },
    'min': {
        'to_list': False,
        'types': [TYPE_DATE, TYPE_NUM]
    },
    'max': {
        'to_list': False,
        'types': [TYPE_DATE, TYPE_NUM]
    }
}
