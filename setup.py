#!/usr/bin/env python
from setuptools import setup
import json
import os


def load_version():
    v_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'async_keepalive_httpc', 'VERSION.json')
    )

    with open(v_path, 'rb') as f:
        v = json.load(f)
        return v['main']

setup(name='Async KeepAlive HTTP client',
      version=load_version(),
      description='An async http client with keep-alive capabilities',
      license='BSD',
      author='Tom Tang',
      author_email='tly1980@gmail.com',
      packages=['async_keepalive_httpc'],
      url="https://github.com/tly1980/async_keepalive_httpc",
      platforms='any',
      package_data={
        'async_keepalive_httpc': ['async_keepalive_httpc/*.json']
      },
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

