import geopandas as gpd
import numpy as np
import pandas as pd
# import matplotlib

import petk.constants as constants
import petk.tools as tools
import petk.validation as validation


class DataReport:
    # TODO: clear validation cache on schema change

    def __init__(self, data, schema={}):
        self.df = data.copy()
        self.df.index.name = 'index'

        self.schema = schema
        for col, dd in self.schema.items():
            assert col in self.df.columns, 'Invalid input schema, column {0} does not exist in data'.format(col)

            for k, v in dd.items():
                if k in ['nulls']:
                    if not isinstance(v, (list, tuple)):
                        self.schema[col][k] = [v]

        for col in self.df.columns:
            extra = self.schema[col]['nulls'] if tools.key_exists(self.schema, col, 'nulls') else []
            self.df[col] = self.df[col].replace(constants.NULLS + extra, np.nan)

        self.description = pd.DataFrame()
        self.validation = pd.DataFrame()

    def introduce(self, as_dict=False):
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
                ('columns', '{0}'.format(tools.get_type(self.df[col]).lower())) for col in self.df.columns
            ]).value_counts()
        )

        if isinstance(self.df, gpd.GeoDataFrame):
            centroid_loc = tools.get_point_location(self.df.centroid)
            has_z = self.df.has_z.value_counts()

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

        return self._format_results(base.append(additions).to_frame(name='values'), as_dict=as_dict)

    def describe(self, columns=[], as_dict=False):
        columns = self._find_columns(columns)

        for c in columns:
            if c not in self.description.columns:
                self.description = pd.concat([ self.description, tools.get_description(self.df[c], name=c) ], axis=1, sort=False)

        return self._format_results(self.description[columns], as_dict=as_dict)

    # TODO: consider return passed when all results are valid
    def validate(self, columns=[], as_dict=False, verbose=False):
        columns = self._find_columns(columns)

        for col, conditions in self.schema.items():
            if col not in columns or \
                ('column' in self.validation.columns and col in self.validation['column'].values):
                continue

            checks = np.intersect1d(
                list(conditions.keys()),
                [method for method in dir(validation) if callable(getattr(validation, method))]
            )

            audits = {}

            if col == 'geometry':
                issues = validation.geospatial(self.df[col])

                if issues is not None:
                    audits['geospatial'] = issues

            for v in checks:
                issues = getattr(validation, v)(self.df[col], conditions[v])

                if issues is not None:
                    audits[v] = issues

            if audits:
                audits = pd.concat(audits.values(), keys=audits.keys()).to_frame().reset_index()
                audits.columns = ['function', 'index', 'notes']
                audits['column'] = col
            else:
                audits = pd.DataFrame()

            self.validation = pd.concat([self.validation, audits])

        results = self.validation.copy()
        if not self.validation.empty:
            results = results[
                results['column'].isin(columns)
            ].sort_values(
                ['column', 'index', 'function']
            ).set_index(
                ['column', 'index', 'function']
            )

        return self._format_results(results, as_dict=as_dict, verbose=verbose)

    def _find_columns(self, columns):
        if not columns:
            columns = self.df.columns
        elif not isinstance(columns, list):
            columns = [columns]

        missing = [x for x in columns if not x in self.df.columns]
        assert not missing, 'Column(s) {0} not in data'.format(', '.join(missing))

        return columns

    def _format_results(self, results, as_dict=False, verbose=False):
        if not results.empty and verbose:
            results = results.join(self.df)

        if as_dict:
            records = {}

            for idx, row in results.iterrows():
                key = idx
                values = records

                if not isinstance(idx, str):
                    for k in idx:
                        if not tools.key_exists(values, k):
                            values[k] = {}

                        if k != idx[-1]:
                            values = values[k]

                    key = idx[-1]

                values[key] = row.to_dict() if row.size > 1 else row.values[0]

            return records

        return results.dropna(how='all', axis=0)
