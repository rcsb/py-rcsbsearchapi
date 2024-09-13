"""RCSB PDB Search API"""

<<<<<<< HEAD
from typing import List
from .search import Terminal, SCHEMA  # noqa: F401
from .search import Attr, AttributeQuery, Group, Query, Session, TextQuery, Value
=======
from typing import TYPE_CHECKING, Any, List

from .schema import Schema
from .search import Terminal, SCHEMA  # noqa: F401
from .search import Attr, AttrLeaf, AttributeQuery, Group, Query, Session, TextQuery, Value
from typing import TYPE_CHECKING
>>>>>>> 5a493e6 (documentation edits and adding page for attribute methods)

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
