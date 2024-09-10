"""RCSB PDB Search API"""

# from typing import TYPE_CHECKING, Any, List

from .schema import Schema
from .search import Terminal  # noqa: F401
from .search import Attr, AttrLeaf, AttributeQuery, Group, Query, Session, TextQuery, Value
from typing import TYPE_CHECKING

__version__ = "1.6.0"

# loading rcsb_attributes can cause errors, so load it lazily
if TYPE_CHECKING:
    from .schema import SchemaGroup

SCHEMA = Schema(Attr, "SchemaGroup")
rcsb_attributes = SCHEMA.rcsb_attributes
# SCHEMA_DICT = Schema(AttrLeaf, "dict")
# rcsb_attributes_dict = SCHEMA_DICT.rcsb_attributes_dict

# if "rcsb_attributes" not in globals():
#     globals()["rcsb_attributes"] = s.rcsb_attrs

# def __dir__() -> List[str]:
#     print("IN DIR")
#     return sorted(__all__)

__all__ = ["Query", "Group", "Attr", "Terminal", "TextQuery", "rcsb_attributes"]
