from importlib.metadata import version

from .buy_ticket import buy_ticket

__version__ = version("niteharts")
__all__ = ["buy_ticket"]
