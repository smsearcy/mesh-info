import sys

if sys.version_info >= (3, 8):
    from importlib.metadata import version
else:
    from importlib_metadata import version  # type: ignore

__version__ = version("pymeshmap")
