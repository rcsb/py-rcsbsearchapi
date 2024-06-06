"""Parse the full RCSB PDB search schema

Provides access to all valid attributes for search queries.
"""

import json
import logging
import pkgutil
import re
import requests
from typing import Any, Iterator, List, Union
from .search import Attr
from .const import STRUCTURE_ATTRIBUTE_SCHEMA_URL, CHEMICAL_ATTRIBUTE_SCHEMA_URL, SEARCH_SCHEMA_URL, STRUCTURE_ATTRIBUTE_SEARCH_SERVICE, CHEMICAL_ATTRIBUTE_SEARCH_SERVICE


def _fetch_schema(url: str):
    "Request the current schema from the web"
    logging.info("Requesting %s", url)
    response = requests.get(url, timeout=None)
    if response.status_code == 200:
        return response.json()
    else:
        logging.debug("HTTP response status code %r", response.status_code)
        return None


def _load_json_schema():
    logging.info("Loading structure schema from file")
    latest = pkgutil.get_data(__package__, "resources/metadata_schema.json")
    return json.loads(latest)


def _load_chem_schema():
    logging.info("Loading chemical schema from file")
    latest = pkgutil.get_data(__package__, "resources/chemical_schema.json")
    return json.loads(latest)


class SchemaGroup:
    """A non-leaf node in the RCSB PDB schema. Leaves are Attr values."""

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


def _make_group(fullname: str, nodeL: List) -> Union[SchemaGroup, Attr]:
    """Represent this node of the schema as a python object

    Params:
    - name: full dot-separated attribute name

    Returns:
    An Attr (Leaf nodes) or SchemaGroup (object nodes)
    """
    group = SchemaGroup()
    for (node, attrtype) in nodeL:
        if "anyOf" in node:
            children = {_make_group(fullname, [(n, attrtype)]) for n in node["anyOf"]}
            # Currently only deal with anyOf in leaf nodes
            assert len(children) == 1, f"type of {fullname} couldn't be determined"
            return next(iter(children))
        if "oneOf" in node:
            children = {_make_group(fullname, [(n, attrtype)]) for n in node["oneOf"]}
            # Currently only deal with oneOf in leaf nodes
            assert len(children) == 1, f"type of {fullname} couldn't be determined"
            return next(iter(children))
        if "allOf" in node:
            children = {_make_group(fullname, [(n, attrtype)]) for n in node["allOf"]}
            # Currently only deal with allOf in leaf nodes
            assert len(children) == 1, f"type of {fullname} couldn't be determined"
            return next(iter(children))
        if node["type"] in ("string", "number", "integer", "date"):
            return Attr(fullname, attrtype)
        elif node["type"] == "array":
            # skip to items
            return _make_group(fullname, [(node["items"], attrtype)])
        elif node["type"] == "object":
            for childname, childnode in node["properties"].items():
                fullchildname = f"{fullname}.{childname}" if fullname else childname
                childgroup = _make_group(fullchildname, [(childnode, attrtype)])
                setattr(group, childname, childgroup)
        else:
            raise TypeError(f"Unrecognized node type {node['type']!r} of {fullname}")
    return group


def _make_schema(structure_schema_url: str, chemical_schema_url: str) -> SchemaGroup:
    json1 = _fetch_schema(structure_schema_url)
    if not json1:
        json1 = _load_json_schema()
    json2 = _fetch_schema(chemical_schema_url)
    if not json2:
        json2 = _load_chem_schema()
    schemas = [(json1, STRUCTURE_ATTRIBUTE_SEARCH_SERVICE), (json2, CHEMICAL_ATTRIBUTE_SEARCH_SERVICE)]
    schema = _make_group("", schemas)
    assert isinstance(schema, SchemaGroup)  # for type checking
    return schema


rcsb_attributes: SchemaGroup
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
            globals()["rcsb_attributes"] = _make_schema(STRUCTURE_ATTRIBUTE_SCHEMA_URL, CHEMICAL_ATTRIBUTE_SCHEMA_URL)
        return globals()["rcsb_attributes"]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    return sorted(__all__)


__all__ = [  # noqa: F822
    "STRUCTURE_ATTRIBUTE_SCHEMA_URL",
    "SEARCH_SCHEMA_URL",
    "CHEMICAL_ATTRIBUTE_SCHEMA_URL",
    "rcsb_attributes",
    "SchemaGroup",
]
