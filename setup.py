#!/usr/bin/env python

#from distutils.core import setup
from setuptools import setup,find_packages

setup(
        name='python-cmssysadmin',
        scripts=['scripts/autoregister', 'scripts/get_token'],
        version='0.3',
        description='CMS Sysadmin python tools',
        author='Jean-Marc ANDRE',
        author_email='jean-marc.andre@cern.ch',
        packages=['cmssysadmin', 'cmssysadmin.foreman', 'cmssysadmin.landb'],
        url='https://github.com/desmo999r/cmssysadmin',
)
# vim: set ts=8 sw=8 tw=0 et :
