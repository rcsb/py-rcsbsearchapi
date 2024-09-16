"""RCSB PDB Search API"""

from typing import List
from .search import Terminal, SCHEMA  # noqa: F401
from .search import Attr, AttributeQuery, Group, Query, TextQuery

__version__ = "1.6.0"

# # loading rcsb_attributes can cause errors, so load it lazily
# if TYPE_CHECKING:
#     from .schema import SchemaGroup

rcsb_attributes = SCHEMA.rcsb_attributes
# SCHEMA_DICT = Schema(AttrLeaf, "dict")
# rcsb_attributes_dict = SCHEMA_DICT.rcsb_attributes_dict

# if "rcsb_attributes" not in globals():
#     globals()["rcsb_attributes"] = s.rcsb_attrs


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
