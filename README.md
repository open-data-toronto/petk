# Pandas Exploration Toolkit

A toolkit to assist data exploration for both tabular and geospatial data. Inspired by [pandas-profiling](https://github.com/pandas-profiling/pandas-profiling).

## Planned Features for v1 Release:
* Visualizations of data
* Correlation analysis

## Requirements
* Python 3.6
* geopandas>=0.4.0

## Installation
    pip install petk

## Usage

```python
import geopandas as gpd
import petk


df = gpd.read_file([data_path])
report = petk.DataReport(df)

# To display a high level description of the data
report.introduce()

# To show a statistical breakdown of the data
report.describe()

# To validate the content of the data, pass a schema on initialization
report = petk.DataReport(df, schema)
report.validate(rules)
```

The schema has to be in a fixed structure with specific keys.

An example of the schema checking all the validation could be:

```python
schema = {
    'col_1': {                                      # A STRING column
        'accepted': ['a', 'b', 'd'],                # Accepted values
        'default': 'a',
        'nulls': ['N/A']                            # Not None or NaN values that should be considered as a null
    },
    'col_2': {                                      # A NUMERIC/DATETIME column
        'range': [np.nan, 4],                       # Possible range of the values, where np.nan represent no bound
        'default': 0,
        'nulls': [-1],                              # Not None or NaN values that should be considered as a null
    },
    'geometry': {
        'sliver': {
            'threshold': 1,                         # Threshold in meter or meter^2 where the geometry is a sliver
            'projected_coordinates': 2019           # Nearest projection to the coordinates of the data
        },
        'bounding_box': [1, 2, 3, 4]                # Bounding box of the data in [xmin, xmax, ymin, ymax]
    }
}
```

## Contribution
All contributions, bug reports, bug fixes, documentation improvements, enhancements and ideas are welcome.

### Reporting issues
Please report issues [here](https://github.com/open-data-toronto/petk/issues).

### Contributing
Please develop in your own branch and create Pull Requests into the `dev` branch when ready for review and merge.

## License

* [MIT License](https://github.com/open-data-toronto/petk/blob/master/LICENSE)
