# Pandas Exploration Toolkit

A toolkit to assist data exploration for both tabular and geospatial data. Inspired by [pandas-profiling](https://github.com/pandas-profiling/pandas-profiling).

## Planned Features for v1 Release:
* Validation against rules for Tabular data
* Visualizations of data
* Correlation analysis

## Requirements
* Python 3.6
* geopandas>=0.4.0

## Installation
    git clone https://github.com/open-data-toronto/petk
    cd petk
    python setup.py install

## Usage

```python
import geopandas as gpd
import petk


df = gpd.read_file([data_path])
report = petk.DataReport(df)

# To display a high level description of the data
report.introduce

# To show a statistical breakdown of the data
report.describe()

# To validate the content of the data against fixed rules (currently only for GeoSpatial data)
report.validate(rules)
```

Where a sample of the rules could be

```python
rules = {
    'geometry': {
        'get_invalids': True,
        'get_slivers': {
            'projection': 2019,
            'area_thresh': 1,
            'length_thresh': 1
        }
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
