"""RCSB PDB Search API"""

from typing import List
from .search import Terminal, SCHEMA  # noqa: F401
from .search import Attr, AttributeQuery, Group, Query, TextQuery

__version__ = "2.0.0"

rcsb_attributes = SCHEMA.rcsb_attributes


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
