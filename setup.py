try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='petk',
    version='0.0.1',
    author='Open Data Toronto',
    author_email='opendata@toronto.ca',
    packages=['petk'],
    url='',
    license='MIT',
    description='',
    install_requires=[],
    include_package_data=True,
    classifiers=[
        'Development Status :: 1 - Planning',
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
