"""
Use this setup for Python3 builds of errator
"""

from distutils.core import setup
from setuptools.extension import Extension
try:
    from Cython.Build import cythonize
except ImportError:
    use_cython = False
else:
    use_cython = True

ext_modules = []
if use_cython:
    ext_modules.extend(cythonize("_errator.pyx"))
else:
    ext_modules.append(Extension("_errator", ["_errator.c"]))

version = "0.3.3"


def get_readme():
    with open("README.rst", "r") as f:
        readme = f.read()
    return readme


setup(
    name="errator",
    ext_modules=ext_modules,
    py_modules=["errator"],
    version=version,
    description="Errator allows you to create human-readable exception narrations",
    long_description=get_readme(),
    author="Tom Carroll",
    author_email="actuator@pobox.com",
    url="https://github.com/haxsaw/errator",
    download_url="https://github.com/haxsaw/errator/archive/%s.tar.gz" % version,
    keywords=["exception", "logging", "traceback", "stacktrace"],
    classifiers=[],
    license="MIT"
)
