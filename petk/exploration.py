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
    # TODO: init schema when schema is update separately

    def __init__(self, data, schema={}, as_dict=False):
        self.df = data
        self.df.index.name = 'index'

        self.schema = self.init_schema(schema)

        self.description = pd.DataFrame()
        self.validation = pd.DataFrame()

        self.as_dict = as_dict

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
            ('observations', 'missing'): np.sum([self.df[col][self.df[col].isin([self.schema[col]['nulls']])].count() for col in self.df.columns])
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

        return self._format_results(base.append(additions).to_frame(name='values'))

    def describe(self, columns=[]):
        '''
        Profile columns by the data type

        Parameters:
        columns (list or str): Identify the columns to profile

        Returns:
        (DataFrame): Profiling report
        '''

        columns = self._find_columns(columns)

        for c in columns:
            if c not in self.description.columns:
                self.description = pd.concat(
                    [
                        self.description,
                        tools.get_description(self.df[c], self.schema[c]['nulls'], name=c)
                    ],
                    axis=1,
                    sort=False
                )

        return self._format_results(self.description[columns])

    def validate(self, columns=[], verbose=False):
        '''
        Validate the data based on input rules for tabular data and geospatial attributes

        Parameters:
        rules   (dict): A dictionary with data columns as keys and rules to validate for the column
        verbose (bool): Identify if the results should be displayed with the original data

        Returns:
        (DataFrame): Validation report
        '''

        columns = self._find_columns(columns)

        for col, checks in self.schema.items():
            if col not in columns or ('column' in self.validation.columns and col in self.validation['column'].values):
                continue

            audit = np.intersect1d(
                list(checks.keys()),
                [method for method in dir(validation) if callable(getattr(validation, method))]
            )

            results = {}

            if col == 'geometry':
                issues = validation.geospatial(self.df[col])

                if issues is not None:
                    results['geospatial'] = issues

            for v in audit:
                issues = getattr(validation, v)(self.df[col], checks[v])

                if issues is not None:
                    results[v] = issues

            vali = pd.concat(results.values(), keys=results.keys()).to_frame().reset_index()
            vali.columns = ['function', 'index', 'notes']
            vali['column'] = col

            self.validation = pd.concat([self.validation, vali])

        return self._format_results(
            self.validation[
                self.validation['column'].isin(columns)
            ].sort_values(
                ['index', 'function']
            ).set_index(
                ['index', 'column', 'function']
            ),
            verbose=verbose
        )

    def init_schema(self, schema):
        base = {
            col: {
                'nulls': constants.NULLS
            } for col in self.df.columns
        }

        for col, dd in schema.items():
            assert col in base, 'Invalid input schema, column {0} does not exist in data'.format(col)

            for k, v in dd.items():
                if k in ['nulls']:
                    base[col][k] = set(v + base[col][k])
                else:
                    base[col][k] = v

        return base

    def _find_columns(self, columns):
        if not columns:
            columns = self.df.columns
        elif not isinstance(columns, list):
            columns = [columns]

        missing = [x for x in columns if not x in self.df.columns]
        assert not missing, 'Columns "{0}" not in data'.format(', '.join(missing))

        return columns

    def _format_results(self, results, verbose=False):
        if verbose:
            results = results.join(self.df)

        if self.as_dict:
            if isinstance(results.index, pd.MultiIndex):
                records = {}

                for idx, row in results.iterrows():
                    _values = records

                    for k in idx:
                        if not tools.key_exists(_values, k):
                            _values[k] = {}

                        if k != idx[-1]:
                            _values = _values[k]

                    _values[idx[-1]] = row.to_dict() if row.size > 1 else row.values[0]

                return records
            else:
                return data.to_dict()

        return results
