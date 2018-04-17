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

version = "0.3.1"


setup(
    name="errator",
    ext_modules=[],
    py_modules=["errator"],
    version=version,
    description="Errator allows you to create human-readable exception narrations",
    author="Tom Carroll",
    author_email="actuator@pobox.com",
    url="https://github.com/haxsaw/errator",
    download_url="https://github.com/haxsaw/errator/archive/%s.tar.gz" % version,
    keywords=["exception", "logging", "traceback", "stacktrace"],
    classifiers=[],
    license="MIT"
)
