from collections import OrderedDict

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
        self.df.index.name = 'index'

        self.description = {}

    @property
    def describe(self):
        '''
        Concatenate the profiling done into a single report

        Returns:
        (DataFrame): Profiling report
        '''

        desc = pd.DataFrame(self.description.values())

        if not desc.empty:
            desc = desc.set_index('name')

        return desc.T

    @property
    def introduce(self):
        '''
        Introduces the high level descriptions of the data

        Returns:
        (DataFrame): Introductory report
        '''

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

        return dd.append(cd).to_frame(name='values')

    def profile_columns(self, columns=[]):
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
            # Skip profiling if the column has already been profiled
            if c not in self.description.keys():
                self.description[c] = self.get_description(c)

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

        description = [
            ('type', dtype),
            ('name', series.name),
            ('memory_usage', series.memory_usage()),
            ('count', count),
            ('p_missing', (series.size - count) / series.size),
            ('n_missing', series.size - count),
        ]

        if not dtype in [constants.TYPE_UNSUPPORTED, constants.TYPE_CONST, constants.TYPE_UNIQUE]:
            n_distinct = series.nunique()

            description += [
                ('distinct_count', n_distinct),
                ('is_unique', n_distinct == series.size),
                ('p_unique', n_distinct * 1.0 / series.size)
            ]

            if dtype == constants.TYPE_BOOL:
                description += [
                    ('mean', series.mean())
                ]
            elif dtype in [constants.TYPE_DATE, constants.TYPE_NUM]:
                n_inf = series.loc[(~np.isfinite(series)) & series.notnull()].size

                description += [
                    ('p_infinite', n_inf / series.size),
                    ('n_infinite', n_inf),
                    ('min', series.min()),
                    ('max', series.max())
                ]

                description += [
                    ('{:.0%}'.format(perc), series.quantile(perc))
                        for perc in [0.05, 0.25, 0.5, 0.75, 0.95]
                ]

                if dtype == constants.TYPE_NUM:
                    n_zeros = series.size - np.count_nonzero(series)

                    description += [
                        ('mean', series.mean()),
                        ('std', series.std()),
                        ('variance', series.var()),
                        ('iqr', series.quantile(0.75) - series.quantile(0.25)),
                        ('kurtosis', series.kurt()),
                        ('skewness', series.skew()),
                        ('sum', series.sum()),
                        ('mad', series.mad()),
                        ('cv', series.std() / series.mean()),
                        ('n_zeros', n_zeros),
                        ('p_zeros', n_zeros / series.size)
                    ]

        # OrderedDict used to fixed the DataFrame column orders
        return OrderedDict(description)

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

class GeoReport:
    def __init__(self, df, verbose=False, **kwargs):
        self.df = df
        self.df.index.name = 'index'

        self.description = {}

        self.verbose = verbose

    @property
    def describe(self):
        '''
        Concatenate the profiling done into a single report

        Returns:
        (DataFrame): Profiling report
        '''

        desc = pd.DataFrame()

        if self.description:
            desc = pd.concat(self.description.values(), keys=self.description.keys()).reset_index()
            desc.rename({
                'level_0': 'issue',
                'level_1': 'index'
            }, axis=1, inplace=True)

            # Sort the MultiIndex by the record index then the issue found
            desc = desc.sort_values('index').set_index(['index', 'issue'])

        # Merge the profiling with original data
        # TODO: perform the merging on a function level instead here (so each function returns the full verbose description)
        if self.verbose:
            desc = self.df.join(desc.drop('geometry', axis=1), how='inner')

        return desc

    @property
    def introduce(self):
        '''
        Introduces the high level descriptions of the data

        Returns:
        (DataFrame): Introductory report
        '''

        z = self.df.has_z.value_counts()

        base = pd.Series({
            'crs': self.df.crs['init'],
            'single_geom_type': self.df.geom_type.nunique() == 1,
            'total_bounds': self.df.total_bounds,
            '3d_shapes': z[True] if True in z.index else 0
        })

        geom = self.df.geom_type.value_counts()

        return base.append(geom).to_frame(name='values')

    def find_invalids(self):
        '''
        Find the invalid geometries within the data

        Returns:
        (DataFrame): Invalid geometries and the reason
        '''

        invalid = gpd.GeoDataFrame(self.df[~self.df.is_valid]['geometry'])

        if not invalid.empty:
            invalid['notes'] = invalid['geometry'].apply(lambda x: explain_validity(x) if not x is None else 'Null geometry')
            self.description['invalid_geometries'] = invalid

            return invalid

    def find_outsiders(self, xmin, xmax, ymin, ymax):
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
        invalid = gpd.GeoDataFrame(self.df.loc[~self.df.index.isin(self.df.cx[xmin:xmax, ymin:ymax].index)]['geometry'])

        if not invalid.empty:
            invalid['notes'] = 'Outside of bbox({0}, {1}, {2}, {3})'.format(xmin, xmax, ymin, ymax)
            self.description['outside_boundaries'] = invalid

            return invalid

    def find_slivers(self, area_thresh=constants.SLIVER_AREA, line_thresh=constants.SLIVER_LINE):
        '''
        Find the slivers within the geometries

        Parameters:
        area_thresh (numeric): Threshold area for a Polygon to be considered a sliver
        line_thresh (numeric): Threshold length for a Line to be considered a sliver

        Returns:
        (DataFrame): Sliver geometries
        '''

        # TODO: How to project to the correct projection?
        pieces = self.df.explode().to_crs({'init': 'epsg:2019', 'units': 'm'})

        slivers = pieces['geometry'].apply(self._is_sliver, args=(area_thresh, line_thresh))
        slivers = slivers[slivers].groupby(level=0).count()

        if not slivers.empty:
            slivers = gpd.GeoDataFrame({
                'geometry': self.df['geometry'],
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
