#!/usr/bin/env python
import sys
if sys.version < '3':
    from distutils.command.build_py import build_py
else:
    from distutils.command.build_py import build_py_2to3 as build_py

from distutils.core import setup

setup(
    cmdclass        = {'build_py': build_py},
    name            = "pycrust",
    version         = "1.0",
    description     = "A collection of add-ons for CherryPy",
    author          = "Michael Stella",
    author_email    = "pycrust@thismetalsky.org",
    license         = "BSD",
    packages        = ['pycrust'],
    install_requires= ['mako', 'routes'],
)

