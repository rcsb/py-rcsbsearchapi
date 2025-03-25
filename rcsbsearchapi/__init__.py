"""RCSB PDB Search API"""

from typing import List
from .search import Terminal, SCHEMA  # noqa: F401
from .search import Attr, AttributeQuery, Group, Query, TextQuery
from warnings import warn

__version__ = "2.0.1"

rcsb_attributes = SCHEMA.rcsb_attributes

warn(
    """Please migrate to the use of our new and improved package, rcsb-api (https://rcsbapi.readthedocs.io/en/latest/),
    which contains all the same functionalities as rcsbsearchapi and more! New features will only be added to the new rcsb-api package.
    For more details, see https://github.com/rcsb/py-rcsbsearchapi/issues/51.""",
    category=DeprecationWarning,
    # Set stacklevel so the warning returns to the caller of the code
    stacklevel=2,
)


def __dir__() -> List[str]:
    return sorted(__all__)


__all__ = [
    "Query",
    "Group",
    "Attr",
    "Terminal",
    "TextQuery",
    "AttributeQuery",
    "rcsb_attributes"
]
