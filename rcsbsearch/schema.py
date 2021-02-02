"""Parse the full RCSB search schema

Provides access to all valid attributes for search queries.
"""

from . import Attr
import requests
import re
from typing import Union, Iterator


def _get_json_schema():
    "Get the current JSON schema from the web"
    url = "http://search.rcsb.org/rcsbsearch/v1/metadata/schema"

    response = requests.get(url)
    response.raise_for_status()
    return response.json()


class SchemaGroup:
    """A non-leaf node in the RCSB schema. Leaves are Attr values."""

    def search(self, pattern: Union[str, re.Pattern], flags=0) -> Iterator[Attr]:
        """Find all attributes in the schema matching a regular expression.

        Returns:
            An iterator supplying Attr objects whose attribute matches.
        """
        matcher = re.compile(pattern, flags=flags)
        return filter(lambda a: matcher.search(a.attribute), self)

    def __iter__(self) -> Iterator[Attr]:
        """Iterate over all leaf nodes

        Example:

            >>> [a for a in attrs if "stoichiometry" in a.attribute]
            [Attr(attribute='rcsb_struct_symmetry.stoichiometry')]

        """

        def leaves(self):
            for k, v in self.__dict__.items():
                if isinstance(v, Attr):
                    yield v
                elif isinstance(v, SchemaGroup):
                    yield from iter(v)
                else:
                    # Shouldn't happen
                    raise TypeError(f"Unrecognized member {k!r}: {v!r}")

        return leaves(self)

    def __str__(self):
        return "\n".join((str(c) for c in self.__dict__.values()))


def _make_group(fullname: str, node) -> Union[SchemaGroup, Attr]:
    """Represent this node of the schema as a python object

    Params:
    - name: full dot-separated attribute name

    Returns:
    An Attr (Leaf nodes) or SchemaGroup (object nodes)
    """
    if node["type"] in ("string", "number", "integer", "date"):
        return Attr(fullname)
    elif node["type"] == "array":
        # skip to items
        return _make_group(fullname, node["items"])
    elif node["type"] == "object":
        group = SchemaGroup()  # parent, name)
        for childname, childnode in node["properties"].items():
            fullchildname = f"{fullname}.{childname}" if fullname else childname
            childgroup = _make_group(fullchildname, childnode)
            setattr(group, childname, childgroup)
        return group
    else:
        raise TypeError(f"Unrecognized node type {node['type']!r} of {fullname}")


def _make_schema():
    json = _get_json_schema()
    return _make_group("", json)


# Note that docstring needs to be set in __init__
rcsb_attributes = _make_schema()
"""Object with all known RCSB attributes.

This is provided to ease autocompletion as compared to creating Attr objects from
strings. For example,
::

    rcsb_attributes.rcsb_nonpolymer_instance_feature_summary.chem_id

is equivalent to
::

    Attr('rcsb_nonpolymer_instance_feature_summary.chem_id')

"""
