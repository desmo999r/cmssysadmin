#!/usr/bin/env python

#from distutils.core import setup
from setuptools import setup,find_packages

setup(
		name='python-cmssysadmin',
		scripts=['scripts/autoregister', 'scripts/get_token'],
		version='0.1',
		description='CMS Sysadmin python tools',
		author='Jean-Marc ANDRE',
		author_email='jean-marc.andre@cern.ch',
		packages=find_packages(exclude=['*django_*']),
)
