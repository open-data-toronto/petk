import numpy as np
import pandas as pd
import matplotlib

import petk.constants as constants
import petk.utils as utils


class DataReport:
    def __init__(self, data):
        self.df = data
        self.history = [] # List of DataProfiles (for now)

    def introduce(self):
        return pd.Series({
            'memory_usage': np.sum(self.df.memory_usage(deep=True)),
            'rows': len(self.df),
            'columns': len(self.df.columns),
            'total_observations': np.prod(self.df.shape),
            'missing_observations': np.sum(len(df) - self.df.count())
        })

    def describe_columns(self):
        return pd.Series([
            utils.get_type(self.df[col]).lower()
        ] for col in self.df.columns).value_counts()

    # MOVE TO DATAPROFILE?
    def correlate(self, how='pearson', visualize=True):
        pass

    def profile(self, columns=self.df.columns):
        pass

    def summarize_profiles(self):
        # Describe number of profiles and how many include visualizations
        pass

    def generate_report(self):
        pass

    def visualize_report(self):
        pass

class DataProfile:
    def __init__(self, array, top=5, visualize=True):
        self.array = array

        dtype = utils.get_type(self.array)
        # TODO: Convert these 2 functions to static functions
        desc = self.get_description()
        fv = self.get_frequent_values(top)

        self.dtype = dtype
        self.description = desc
        self.frequent_values = fv

    def get_description(self):
        count = self.array.count() # ONLY non-NaN observations

        description = {
            'type': self.dtype,
            'memory_usage': self.array.memory_usage(),
            'count': count,
            'p_missing': (self.array.size - count) / self.array.size,
            'n_missing': self.array.size - count,
        }

        if not self.dtype in [constants.TYPE_UNSUPPORTED, constants.TYPE_CONST, constants.TYPE_UNIQUE]:
            n_distinct = self.array.nunique()

            description.update({
                'distinct_count': distinct_count,
                'is_unique': distinct_count == self.array.size,
                'p_unique': distinct_count * 1.0 / self.array.size
            })

            if self.dtype == constants.TYPE_BOOL:
                description.update({
                    'mean': self.array.mean()
                })
            elif self.dtype in [constants.TYPE_DATE, constants.TYPE_NUM]:
                n_inf = self.array.loc[(~np.isfinite(self.array)) & self.array.notnull()].size

                description.update({
                    'p_infinite': n_inf / self.array.size,
                    'n_infinite': n_inf,
                    'min': self.array.min(),
                    'max': self.array.max()
                })

                for perc in np.array([0.05, 0.25, 0.5, 0.75, 0.95]):
                    description['{:.0%}'.format(perc)] = self.array.quantile(perc)

                if self.dtype == constants.TYPE_NUM:
                    n_zeros = self.array.size - np.count_nonzero(self.array)

                    description.update({
                        'mean': self.array.mean(),
                        'std': self.array.std(),
                        'variance': self.array.var(),
                        'iqr': self.array.quantile(0.75) - self.array.quantile(0.25),
                        'kurtosis': self.array.kurt(),
                        'skewness': self.array.skew(),
                        'sum': self.array.sum(),
                        'mad': self.array.mad(),
                        'cv': self.array.std() / self.array.mean(),
                        'n_zeros': n_zeros,
                        'p_zeros': n_zeros / self.array.size
                    })

        return description

    def get_frequent_values(self, top):
        return self.array.value_counts(dropna=False).head(top)

    def get_distribution(self, top):
        assert self.dtype in [constants.STR, constants.DATE, constants.NUM], 'Distribution not available'

        if self.dtype == constants.STR:
            # Histogram of most frequen top values
            pass
        else:
            # Distribution Plot
            pass
