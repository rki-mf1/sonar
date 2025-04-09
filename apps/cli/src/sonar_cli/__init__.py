from importlib.metadata import metadata
from importlib.metadata import version

__version__ = version(__name__)
VERSION = __version__
NAME = metadata(__name__)["Name"]
