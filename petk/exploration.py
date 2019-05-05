from shapely.validation import explain_validity

import geopandas as gpd
import numpy as np
import pandas as pd
import matplotlib

import petk.constants as constants
import petk.utils as utils


class DataReport:
    def __init__(self, data):
        self.df = data

        self.description = {}

    @property
    def describe(self):
        keys = []
        for k, v in self.description.items():
            if len(v.description.keys()) > len(keys):
                keys = v.description.keys()

        return pd.DataFrame(
            [x.description for x in self.description.values()],
            columns=keys
        ).set_index('column').T

    def visualize(self):
        pass

    def summarize(self):
        pass

    def introduce(self):
        dd = pd.Series({
            'memory_usage': np.sum(self.df.memory_usage(deep=True)),
            'rows': len(self.df),
            'columns': len(self.df.columns),
            'observations: total': np.prod(self.df.shape),
            'observations: missing': np.sum(len(self.df) - self.df.count())
        })

        cd = pd.Series([
            'columns: {0}'.format(utils.get_type(self.df[col]).lower()) for col in self.df.columns
        ]).value_counts()

        return dd.append(cd)

    def profile_columns(self, columns=[]):
        # TODO: assert kwargs

        if not columns:
            columns = self.df.columns

        for col in columns:
            if col not in self.description.keys():
                self.description[col] = DataProfile(self.df[col])

class DataProfile:
    def __init__(self, series):
        self.series = series

        dtype = utils.get_type(self.series)
        self.dtype = dtype

        desc = self.get_description()
        self.description = desc

        # fv = self.get_frequent_values(top)
        # self.frequent_values = fv

    def get_description(self):
        count = self.series.count() # ONLY non-NaN observations

        description = {
            'type': self.dtype,
            'column': self.series.name,
            'memory_usage': self.series.memory_usage(),
            'count': count,
            'p_missing': (self.series.size - count) / self.series.size,
            'n_missing': self.series.size - count,
        }

        if not self.dtype in [constants.TYPE_UNSUPPORTED, constants.TYPE_CONST, constants.TYPE_UNIQUE]:
            n_distinct = self.series.nunique()

            description.update({
                'distinct_count': n_distinct,
                'is_unique': n_distinct == self.series.size,
                'p_unique': n_distinct * 1.0 / self.series.size
            })

            if self.dtype == constants.TYPE_BOOL:
                description.update({
                    'mean': self.series.mean()
                })
            elif self.dtype in [constants.TYPE_DATE, constants.TYPE_NUM]:
                n_inf = self.series.loc[(~np.isfinite(self.series)) & self.series.notnull()].size

                description.update({
                    'p_infinite': n_inf / self.series.size,
                    'n_infinite': n_inf,
                    'min': self.series.min(),
                    'max': self.series.max()
                })

                for perc in [0.05, 0.25, 0.5, 0.75, 0.95]:
                    description['{:.0%}'.format(perc)] = self.series.quantile(perc)

                if self.dtype == constants.TYPE_NUM:
                    n_zeros = self.series.size - np.count_nonzero(self.series)

                    description.update({
                        'mean': self.series.mean(),
                        'std': self.series.std(),
                        'variance': self.series.var(),
                        'iqr': self.series.quantile(0.75) - self.series.quantile(0.25),
                        'kurtosis': self.series.kurt(),
                        'skewness': self.series.skew(),
                        'sum': self.series.sum(),
                        'mad': self.series.mad(),
                        'cv': self.series.std() / self.series.mean(),
                        'n_zeros': n_zeros,
                        'p_zeros': n_zeros / self.series.size
                    })

        return description

    # def get_frequent_values(self, top):
    #     return self.series.value_counts(dropna=False).head(top)
    #
    # def get_distribution(self, top):
    #     assert self.dtype in [constants.STR, constants.DATE, constants.NUM], 'Distribution not available'
    #
    #     if self.dtype == constants.STR:
    #         # Histogram of most frequen top values
    #         pass
    #     else:
    #         # Distribution Plot
    #         pass

class GeoReport:
    def __init__(self, series, **kwargs):
        self.series = series
        self.description = {}

    @property
    def describe(self):
        return pd.concat(self.description.values(), keys=self.description.keys(), sort=False).swaplevel(0, 1)

    def find_invalids(self):
        invalid = gpd.GeoDataFrame(self.series[~self.series.is_valid])

        if not invalid.empty:
            invalid['notes'] = invalid['geometry'].apply(lambda x: explain_validity(x) if not x is None else 'Null geometry')
            self.description['invalid_geometries'] = invalid

            return invalid

    def find_outsiders(self, xmin, xmax, ymin, ymax):
        # TODO: assert bbox

        # There has to be a better way to select outside of a bounding box...
        invalid = gpd.GeoDataFrame(self.series.loc[~self.series.index.isin(self.series.cx[xmin:xmax, ymin:ymax].index)])

        if not invalid.empty:
            invalid['notes'] = 'Outside of bbox({0}, {1}, {2}, {3})'.format(xmin, xmax, ymin, ymax)
            self.description['outside_boundaries'] = invalid

            return invalid

    def find_slivers(self, area_thresh=constants.SLIVER_AREA, line_thresh=constants.SLIVER_LINE):
        pieces = self.series.explode().to_crs({'init': 'epsg:2019', 'units': 'm'})

        slivers = pieces.apply(self._is_sliver, args=(area_thresh, line_thresh))
        slivers = slivers[slivers].groupby(level=0).count()

        if not slivers.empty:
            slivers = gpd.GeoDataFrame({
                'geometry': self.series,
                'notes': slivers.apply(lambda x: '{0} slivers found within geometry'.format(x))
            }).dropna()
            self.description['slivers'] = slivers

            return slivers

    def _is_sliver(self, x, area_thresh, line_thresh):
        if 'polygon' in x.geom_type.lower():
            return x.area < area_thresh
        elif 'linestring' in x.geom_type.lower():
            return x.length < line_thresh
        else:   # Points
            return False
