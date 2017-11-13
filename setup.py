#!/usr/bin/env python3

from setuptools import setup, find_packages
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
    author="Y.Jace Liu, Jensen Zhang, Kai Gao",
    author_email="yang.jace.liu@linux.com, hack@jensen-zhang.site, emiapwil@gmail.com",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Development Status :: 2 - Pre-Alpha",
        "Intented Audience :: Developers",
        "Topic :: System :: Emulators",
    ],
    license="MIT",
    long_description=read("README.rst"),
    packages=find_packages(),
    package_data={"alto.unicorn": ["schema/*.yaml"]},
    scripts=files('bin'),
    zip_safe=False
)
