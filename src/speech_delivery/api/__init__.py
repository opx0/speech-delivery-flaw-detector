"""The HTTP API. Importing it must stay light: the real analyzer is built in `__main__`."""

from .app import create_app

__all__ = ["create_app"]
