#!/usr/bin/env python
from setuptools import setup
import json
import os

VERSION = None

current_folder = os.path.abspath(
    os.path.dirname(__file__)
    )

with open (os.path.join(current_folder, 'VERSION.json'), 'rb') as f:
    v = json.load(f)
    VERSION = v['main']


setup(name='Async Keep-Alive http client',
      version=VERSION,
      description='An async http client with keep-alive capabilities',
      author='Tom Tang',
      author_email='tly1980@gmail.com',
      packages=['async_keepalive_httpc'],
      url="https://github.com/tly1980/async_keepalive_httpc",
      platforms='any',

      install_requires = [
        'tornado>=3.0',
        'botocore>=0.20.0',
        'xmltodict>=0.8.0',
      ],

      classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)

