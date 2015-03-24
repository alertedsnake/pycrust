#!/usr/bin/env python
try:
    from setuptools import setup, find_packages
except:
    from distutils.core import setup, find_packages

setup(
    name            = "pycrust",
    version         = "1.2",
    description     = "A collection of add-ons for CherryPy",
    author          = "Michael Stella",
    author_email    = "pycrust@thismetalsky.org",
    license         = "BSD",
    packages        = find_packages(),
    requires        = ['six'],
    install_requires= ['six'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
    ]
)

