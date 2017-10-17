#!/usr/bin/env python

from setuptools import setup
from os import path, listdir


def read(fname):
    return open(path.join(path.dirname(__file__), fname)).read()


def files(dirname):
    return [path.join(dirname, filename) for filename in listdir(dirname)]


setup(
    name="alto-unicorn",
    version="0.1",
    description="An unicorn as a platform of job placement scheduler",
    url="https://github.com/openalto/alto-unicorn",
    author="Jensen Zhang, Jace Liu",
    author_email="hack@jensen-zhang.site, yang.jace.liu@linux.com",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Development Status :: 2 - Pre-Alpha",
        "Intented Audience :: Developers",
        "Topic :: System :: Emulators",
    ],
    license="MIT",
    long_description=read("README.rst"),
    packages=['alto.unicorn'],
    scripts=files('bin'),
    zip_safe=False
)
