"""
Use this setup for Python3 builds of errator
"""

from distutils.core import setup
from Cython.Build import cythonize

ext_modules = []
ext_modules.extend(cythonize("_errator.pyx",
                             compiler_directives={'language_level': '3',
                                                  'embedsignature': True}))

version = "0.4"


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
    author_email="tcarroll@incisivetech.co.uk",
    url="https://github.com/haxsaw/errator",
    download_url="https://github.com/haxsaw/errator/archive/%s.tar.gz" % version,
    keywords=["exception", "logging", "traceback", "stacktrace"],
    classifiers=[],
    license="MIT"
)
