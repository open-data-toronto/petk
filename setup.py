from setuptools import setup

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='petk',
    version='0.0.2',
    author='Open Data Toronto',
    author_email='opendata@toronto.ca',
    packages=['petk'],
    url='https://github.com/open-data-toronto/petk',
    license='MIT',
    description='A toolkit to assist data exploration for both tabular and geospatial data',
    long_description=long_description,
    install_requires=[
        'geopandas>=0.4.0'
    ],
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Framework :: IPython',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering',
    ],
    keywords='',
)
