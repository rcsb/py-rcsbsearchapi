"""RCSB PDB Search API"""
from typing import TYPE_CHECKING, Any, List

from .search import Terminal  # noqa: F401
from .search import Attr, Group, Query, Session, TextQuery, Value

__version__ = "1.0.0"


# loading rcsb_attributes can cause errors, so load it lazily
if TYPE_CHECKING:
    from .schema import SchemaGroup


# Set docstring at top level too. Keep synchronized with schema.rcsb_attributes
rcsb_attributes: "SchemaGroup"
"""Object with all known RCSB PDB attributes.

This is provided to ease autocompletion as compared to creating Attr objects from
strings. For example,
::

    rcsb_attributes.rcsb_nonpolymer_instance_feature_summary.chem_id

is equivalent to
::

    Attr('rcsb_nonpolymer_instance_feature_summary.chem_id')

All attributes in `rcsb_attributes` can be iterated over.

    >>> [a for a in rcsb_attributes if "stoichiometry" in a.attribute]
    [Attr(attribute='rcsb_struct_symmetry.stoichiometry')]

Attributes matching a regular expression can also be filtered:

    >>> list(rcsb_attributes.search('rcsb.*stoichiometry'))
    [Attr(attribute='rcsb_struct_symmetry.stoichiometry')]a

"""


def __getattr__(name: str) -> Any:
    # delay instantiating rcsb_attributes until it is needed
    if name == "rcsb_attributes":
        if "rcsb_attributes" not in globals():
            from .schema import rcsb_attributes as attrs

            globals()["rcsb_attributes"] = attrs
        return globals()["rcsb_attributes"]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    return sorted(__all__)


__all__ = [
    "Query",
    "Group",
    "Terminal",
    "TextQuery",
    "Session",
    "Attr",
    "Value",
    "rcsb_attributes",
]
