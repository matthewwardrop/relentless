#!/usr/bin/env python2

from distutils.core import setup

setup(name='relentless',
      version='0.2',
      description='A library to assist in testing of programming competition solutions.',
      author='Matthew Wardrop',
      author_email='mister.wardrop@gmail.com',
      url='http://www.matthewwardrop.info/',
      #package_dir={'parameters':'.'},
      #download_url='https://github.com/matthewwardrop/python-relentless',
      packages=['relentless','relentless.utils'],
      package_data = {'relentless': ['Makefile'],'relentless.utils': ['templates/*.tex']},
      requires=['parampy','gitpython','numpy'],
      scripts=['scripts/relentless']

     )
