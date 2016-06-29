from distutils.core import setup

from errator import __version__

setup(
    name="errator",
    py_modules=["errator"],
    version=__version__,
    description="Errator allows you to create human-readable exception narrations",
    author="Tom Carroll",
    author_email="actuator@pobox.com",
    url="https://github.com/haxsaw/errator",
    download_url="https://github.com/haxsaw/errator/tarball/0.1.2",
    keywords=["exception", "logging", "traceback", "stacktrace"],
    classifiers=[],
)
