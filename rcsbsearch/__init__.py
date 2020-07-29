"""RCSB Search API"""
from .search import (
    Query,
    Group,
    Terminal,
    TextQuery,
    Session,
    Attr,
    Value,
)  # noqa: F401

from .schema import rcsb_attributes

# Set docstring at top level too. Keep synchronized with schema.rcsb_attributes
rcsb_attributes = rcsb_attributes
"""Object with all known RCSB attributes.

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

__version__ = "0.2.2-dev0"

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
