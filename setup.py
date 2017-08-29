from __future__ import unicode_literals

import re

from setuptools import find_packages, setup


def get_version(filename):
    with open(filename) as fh:
        metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", fh.read()))
        return metadata['version']


setup(
    name='Mopidy-B2bradio',
    version=get_version('mopidy_b2bradio/__init__.py'),
    url='https://Muzis@bitbucket.org/Muzis/mopidy_b2bradio.git',
    license='Apache License, Version 0.1.1',
    author='Aleksey Sharf',
    author_email='a.sharf@muzis.ru',
    description='Mopidy extension for playing music from b2bradio service',
    long_description=open('README.rst').read(),
    packages=find_packages(exclude=['tests', 'tests.*']),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'setuptools',
        'Mopidy >= 2.1',
        'Pykka >= 1.1',
        'requests >= 2.0',
        'cachetools >= 1.0',
        'python-mpd2 > 0.5',
        'futures >= 3.1.1'
    ],
    entry_points={
        'mopidy.ext': [
            'b2bradio = mopidy_b2bradio:B2bradioExtension',
        ],
    },
    classifiers=[
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Multimedia :: Sound/Audio :: Players',
    ],
)
