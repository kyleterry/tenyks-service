#!/usr/bin/env python
from setuptools import setup

version = '2.1.5'

packages = [
    'tenyksservice',
    'tenyksservice.packages',
]

with open('README.md') as f:
    long_description = f.read()

setup(name='tenyksservice',
      version=version,
      description="Tenyks service class for making fun things for Tenyks.",
      long_description=long_description,
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='irc bot zeromq service',
      author='Kyle Terry',
      author_email='kyle@kyleterry.com',
      url='https://github.com/kyleterry/tenyks-service',
      license='LICENSE',
      packages=packages,
      package_dir={'tenyksservice': 'tenyksservice'},
      package_data={'': ['README.md', 'LICENSE'], 'tenyksservice': ['settings.py.dist']},
      include_package_data=True,
      zip_safe=False,
      test_suite='tests',
      install_requires=[
          'jinja2',
          'pyzmq',
          'aiozmq'
      ],
      entry_points={
          'console_scripts': [
              'tenyks-service-mkconfig = tenyksservice.config:make_config'
          ]
      },
      )
