from distutils.core import setup
import setuptools
from Cython.Build import cythonize


# from errator import __version__

setup(
    name="errator",
    ext_modules=cythonize("_errator.pyx"),
    py_modules=["errator"],
    version="0.3",
    description="Errator allows you to create human-readable exception narrations",
    author="Tom Carroll",
    author_email="actuator@pobox.com",
    url="https://github.com/haxsaw/errator",
    download_url="https://github.com/haxsaw/errator/tarball/%s" % "0.3",
    keywords=["exception", "logging", "traceback", "stacktrace"],
    classifiers=[],
    license="MIT"
)
