"""
Use this setup file if building for Python 2.x
"""

from distutils.core import setup
import setuptools
from Cython.Build import cythonize

version = "0.3"


setup(
    name="errator",
    ext_modules=cythonize("_errator.pyx", language_level=2),
    py_modules=["errator"],
    version=version,
    description="Errator allows you to create human-readable exception narrations",
    author="Tom Carroll",
    author_email="actuator@pobox.com",
    url="https://github.com/haxsaw/errator",
    download_url="https://github.com/haxsaw/errator/tarball/%s" % version,
    keywords=["exception", "logging", "traceback", "stacktrace"],
    classifiers=[],
    license="MIT"
)
