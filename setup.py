#!/usr/bin/env python
from setuptools import setup

version = '1.4'

packages = [
    'tenyksservice',
]

setup(name='tenyksservice',
    version=version,
    description="Tenyks service class for making fun things",
    long_description="""\
""",
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='irc bot redis service',
    author='Kyle Terry',
    author_email='kyle@kyleterry.com',
    url='https://github.com/kyleterry/tenyks-service',
    license='LICENSE',
    packages=packages,
    package_dir={'tenyksservice': 'tenyksservice'},
    package_data={'tenyksservice': ['*.dist']},
    include_package_data=True,
    zip_safe=False,
    test_suite='tests',
    install_requires=[
        'gevent',
        'redis',
        'nose',
        'unittest2',
        'clint',
        'peewee',
        'jinja2',
    ],
    entry_points={
        'console_scripts': [
            'tenyks-service-mkconfig = tenyksservice.config:make_config'
        ]
    },
)
