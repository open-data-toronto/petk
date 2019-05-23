from shapely.geometry import MultiPoint

import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
# import matplotlib

import petk.constants as constants
import petk.tools as tools
import petk.validation as validation


class DataReport:
    def __init__(self, data, schema={}, verbose=False):
        self.df = data
        self.df.index.name = 'index'

        self.description = pd.DataFrame()
        self.schema = schema

    @property
    def introduce(self):
        '''
        Introduces the high level descriptions of the data

        Returns:
        (DataFrame): Introductory report
        '''

        null_counts = []
        for col in self.df.columns:
            missing = constants.NULLS.copy()

            if tools.key_exists(self.schema, col, 'nulls'):
                missing += self.schema[col]['nulls']

            null_counts.append(self.df[col][self.df[col].isin([missing])].count())

        base = pd.Series({
            ('basic', 'memory_usage'): np.sum(self.df.memory_usage(deep=True)),
            ('basic', 'rows'): len(self.df),
            ('basic', 'columns'): len(self.df.columns),
            ('observations', 'total'): np.prod(self.df.shape),
            ('observations', 'missing'): null_counts.sum()
        })

        additions = []

        additions.append(
            pd.Series([
            ('columns', '{0}'.format(tools.get_type(self.df[col]).lower())) for col in self.df.columns
            ]).value_counts()
        )

        if isinstance(self.df, gpd.GeoDataFrame):
            has_z = self.df.has_z.value_counts()
            centroid_loc = tools.get_point_location(MultiPoint(self.df.centroid))

            additions.append(
                pd.Series({
                    ('geospatial', 'crs'): self.df.crs['init'],
                    ('geospatial', 'centroid_location'): centroid_loc,
                    ('geospatial', 'bounds'): self.df.total_bounds,
                    ('geospatial', '3d_shapes'): has_z[True] if True in has_z.index else 0
                })
            )

            geom_types = self.df.geom_type.value_counts()
            geom_types.index = [('geospatial', '{0}s'.format(x.lower())) for x in geom_types.index]
            additions.append(geom_types)

        return base.append(additions).to_frame(name='values')

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
                missing = constants.NULLS.copy()

                if tools.key_exists(self.schema, c, 'nulls'):
                    missing += self.schema[c]['nulls']

                self.description = pd.concat(
                    [
                        self.description,
                        tools.get_description(self.df[c], missing, name=c)
                    ],
                    axis=1,
                    sort=False
                )

        return self.description[columns]

    def validate(self, verbose=False):
        '''
        Validate the data based on input rules for tabular data and geospatial attributes

        Parameters:
        rules   (dict): A dictionary with data columns as keys and rules to validate for the column
        verbose (bool): Identify if the results should be displayed with the original data

        Returns:
        (DataFrame): Validation report
        '''

        results = {}

        for column, checks in self.schema.items():
            audit = np.intersect1d(
                list(checks.keys()),
                [method for method in dir(validation) if callable(getattr(validation, method))]
            )

            if column == 'geometry':
                results['geospatial'] = [validation.geospatial(self.df[column])]

            for v in audit:
                issues = getattr(validation, v)(self.df[column], checks[v])

                if issues is not None:
                    if v not in results:
                        results[v] = []

                    results[v].append(issues)

        if results:
            results = pd.concat([pd.concat(r, keys=[x.name for x in r]) for r in results.values()], keys=results.keys()).to_frame().reset_index()

            results.columns = ['function', 'column', 'index', 'notes']
            results = results.sort_values('index').set_index(['index', 'column', 'function'])

            if verbose:
                results = results.join(self.df, how='inner')

        return results