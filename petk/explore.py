from collections import OrderedDict

from shapely.validation import explain_validity

import geopandas as gpd
import numpy as np
import pandas as pd
import matplotlib

import petk.constants as constants
import petk.utils as utils


class DataReport:
    def __init__(self, data, verbose=False):
        self.df = data
        self.df.index.name = 'index'

        self.description = pd.DataFrame()

    @property
    def introduce(self):
        '''
        Introduces the high level descriptions of the data

        Returns:
        (DataFrame): Introductory report
        '''

        base = pd.Series({
            ('basic', 'memory_usage'): np.sum(self.df.memory_usage(deep=True)),
            ('basic', 'rows'): len(self.df),
            ('basic', 'columns'): len(self.df.columns),
            ('observations', 'total'): np.prod(self.df.shape),
            ('observations', 'missing'): np.sum(len(self.df) - self.df.count())
        })

        additions = []

        additions.append(
            pd.Series([
            ('columns', '{0}'.format(utils.get_type(self.df[col]).lower())) for col in self.df.columns
            ]).value_counts()
        )

        if isinstance(self.df, gpd.GeoDataFrame):
            has_z = self.df.has_z.value_counts()
            additions.append(
                pd.Series({
                    ('geospatial', 'crs'): self.df.crs['init'],
                    ('geospatial', 'bounds'): self.df.total_bounds,
                    ('geospatial', '3d_shapes'): has_z[True] if True in has_z.index else 0
                })
            )

            geom_types = self.df.geom_type.value_counts()
            geom_types.index = [('geospatial', '{0}s'.format(x.lower())) for x in geom_types.index]
            additions.append(geom_types)

        return base.append(additions).to_frame(name='values')

    def validate(self, rules, verbose=False):
        '''
        Validate the data based on input rules for tabular data and geospatial attributes

        Parameters:
        rules (dict): A dictionary with data columns as keys and rules to validate for the column

        Returns:
        (DataFrame): Validation report
        '''

        validation = {}

        for column, rule in rules.items():
            dtype = utils.get_type(self.df[column])

            if dtype in [constants.TYPE_GEO]:
                for func, kwargs in rule.items():
                    if isinstance(kwargs, bool) and kwargs:
                        kwargs = {}

                    validation[func] = getattr(self, func)(**kwargs)
            else:
                pass

        validation = pd.concat(validation.values(), keys=validation.keys(), sort=False).reset_index()
        validation.rename({
            'level_0': 'function',
            'level_1': 'index'
        }, axis=1, inplace=True)

        # Sort the MultiIndex by the record index then the issue found
        validation = validation.sort_values('index').set_index(['index', 'function'])

        # TODO: perform the merging on a function level instead here (so each function returns the full verbose description)
        # if verbose:
        #     desc = self.df.join(desc.drop('geometry', axis=1), how='inner')

        return validation

    def describe(self, columns=[]):
        '''
        Profile columns by the data type

        Parameters:
        columns (list or str): Identify the columns to profile

        Returns:
        (DataFrame): Profiling report
        '''

        if not columns:
            columns = self.df.columns
        elif not isinstance(columns, list):
            columns = [columns]

        # Validate if the column exists within the data
        miss = [x for x in columns if not x in self.df.columns]
        assert not miss, 'Columns "{0}" not in data'.format(', '.join(miss))

        for c in columns:
            if c not in self.description.columns:
                self.description = pd.concat([self.description, self.get_description(c)], axis=1, sort=False)

        return self.description[columns]

    def get_description(self, column):
        '''
        Profile a single data column

        Parameters:
        columns (str): Identify the column to profile

        Returns:
        (OrderedDict): Profile result
        '''

        series = self.df[column]

        count = series.count() # ONLY non-NaN observations
        dtype = utils.get_type(series)

        description = {
            'type': dtype,
            'column': series.name,
            'memory_usage': series.memory_usage(),
            'count': count,
            'p_missing': (series.size - count) / series.size,
            'n_missing': series.size - count,
        }

        if not dtype in [constants.TYPE_UNSUPPORTED, constants.TYPE_CONST, constants.TYPE_UNIQUE, constants.TYPE_GEO]:
            n_distinct = series.nunique()

            description.update({
                'distinct_count': n_distinct,
                'is_unique': n_distinct == series.size,
                'p_unique': n_distinct * 1.0 / series.size
            })

            if dtype == constants.TYPE_BOOL:
                description.update({
                    'mean': series.mean()
                })
            elif dtype in [constants.TYPE_DATE, constants.TYPE_NUM]:
                n_inf = series.loc[(~np.isfinite(series)) & series.notnull()].size

                description.update({
                    'p_infinite': n_inf / series.size,
                    'n_infinite': n_inf,
                    'min': series.min(),
                    'max': series.max()
                })

                for perc in [0.05, 0.25, 0.5, 0.75, 0.95]:
                    description['{:.0%}'.format(perc)] = series.quantile(perc)

                if dtype == constants.TYPE_NUM:
                    n_zeros = series.size - np.count_nonzero(series)

                    description.update({
                        'mean': series.mean(),
                        'std': series.std(),
                        'variance': series.var(),
                        'iqr': series.quantile(0.75) - series.quantile(0.25),
                        'kurtosis': series.kurt(),
                        'skewness': series.skew(),
                        'sum': series.sum(),
                        'mad': series.mad(),
                        'cv': series.std() / series.mean(),
                        'n_zeros': n_zeros,
                        'p_zeros': n_zeros / series.size
                    })

        # OrderedDict used to fixed the DataFrame column orders
        return pd.DataFrame(pd.Series(description, name=column))

    def get_invalids(self):
        '''
        Find the invalid geometries within the data

        Returns:
        (DataFrame): Invalid geometries and the reason
        '''

        invalid = gpd.GeoDataFrame(self.df[~self.df.is_valid])

        if not invalid.empty:
            invalid['notes'] = invalid['geometry'].apply(lambda x: explain_validity(x) if not x is None else 'Null geometry')

        return invalid

    def get_outsiders(self, xmin, xmax, ymin, ymax):
        '''
        Find the geometries outside of a certain bounding box

        Parameters:
        xmin (numeric): Min X of the bounding box
        xmax (numeric): Max X of the bounding box
        ymin (numeric): Min Y of the bounding box
        ymax (numeric): Max Y of the bounding box

        Returns:
        (DataFrame): Out of bound geometries
        '''

        assert xmin < xmax and ymin < ymax, 'Invalid bounding box'

        # TODO: There has to be a better way to select outside of a bounding box...
        invalid = gpd.GeoDataFrame(self.df.loc[~self.df.index.isin(self.df.cx[xmin:xmax, ymin:ymax].index)])

        if not invalid.empty:
            invalid['notes'] = 'Outside of bbox({0}, {1}, {2}, {3})'.format(xmin, xmax, ymin, ymax)

        return invalid

    # TODO: Estimate projection or force projection input
    def get_slivers(self, projection=2019, area_thresh=constants.SLIVER_AREA, length_thresh=constants.SLIVER_LINE):
        '''
        Find the slivers within the geometries

        Parameters:
        area_thresh (numeric): Threshold area for a Polygon to be considered a sliver
        length_thresh (numeric): Threshold length for a Line to be considered a sliver

        Returns:
        (DataFrame): Sliver geometries
        '''

        def is_sliver(x, area_thresh, length_thresh):
            if 'polygon' in x.geom_type.lower():
                return x.area < area_thresh
            elif 'linestring' in x.geom_type.lower():
                return x.length < length_thresh
            else:   # Points
                return False

        pieces = self.df.explode().to_crs({'init': 'epsg:{0}'.format(projection), 'units': 'm'})

        slivers = pieces['geometry'].apply(is_sliver, args=(area_thresh, length_thresh))
        slivers = slivers[slivers].groupby(level=0).count()

        # if not slivers.empty:
        slivers = gpd.GeoDataFrame({
            'notes': slivers.apply(lambda x: '{0} slivers found within geometry'.format(x))
        }).dropna().join(self.df)

        return slivers

    # def get_frequent_values(self, top):
    #     return series.value_counts(dropna=False).head(top)
    #
    # def get_distribution(self, top):
    #     assert dtype in [constants.STR, constants.DATE, constants.NUM], 'Distribution not available'
    #
    #     if dtype == constants.STR:
    #         # Histogram of most frequen top values
    #         pass
    #     else:
    #         # Distribution Plot
    #         pass
