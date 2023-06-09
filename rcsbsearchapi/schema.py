"""Parse the full RCSB search schema

Provides access to all valid attributes for search queries.
"""

import json
import logging
import os
import pkgutil
import re
from typing import Any, Iterator, List, Union

import requests

from .search import Attr

METADATA_SCHEMA_URL = "http://search.rcsb.org/rcsbsearch/v2/metadata/schema"
SEARCH_SCHEMA_URL = "http://search.rcsb.org/json-schema-rcsb_search_query.json"

ENV_RCSBSEARCH_DOWNLOAD_SCHEMA = "RCSBSEARCH_DOWNLOAD_SCHEMA"


def _get_json_schema(download=None):
    """Get the JSON schema

    The RCSBSEARCH_DOWNLOAD_SCHEMA environmental variable controls whether
    to download the schema from the web each time vs using the version shipped
    with rcsbsearchapi
    """
    if download is True or (
        download is None
        and (
            os.environ.get(ENV_RCSBSEARCH_DOWNLOAD_SCHEMA, "no").lower()
            in ("1", "yes", "y")
        )
    ):
        return _download_json_schema()
    return _load_json_schema()


def _download_json_schema():
    "Get the current JSON schema from the web"
    url = METADATA_SCHEMA_URL

    logging.info("Downloading %s", url)
    response = requests.get(url, timeout=None)
    response.raise_for_status()
    return response.json()


def _load_json_schema():
    logging.info("Loading schema from file")
    latest = pkgutil.get_data(__package__, "resources/metadata_schema.json")
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


def _make_group(fullname: str, node) -> Union[SchemaGroup, Attr]:
    """Represent this node of the schema as a python object

    Params:
    - name: full dot-separated attribute name

    Returns:
    An Attr (Leaf nodes) or SchemaGroup (object nodes)
    """
    if "anyOf" in node:
        children = {_make_group(fullname, n) for n in node["anyOf"]}
        # Currently only deal with anyOf in leaf nodes
        assert len(children) == 1, f"type of {fullname} couldn't be determined"
        return next(iter(children))
    if "oneOf" in node:
        children = {_make_group(fullname, n) for n in node["oneOf"]}
        # Currently only deal with oneOf in leaf nodes
        assert len(children) == 1, f"type of {fullname} couldn't be determined"
        return next(iter(children))
    if "allOf" in node:
        children = {_make_group(fullname, n) for n in node["allOf"]}
        # Currently only deal with allOf in leaf nodes
        assert len(children) == 1, f"type of {fullname} couldn't be determined"
        return next(iter(children))
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


def _make_schema() -> SchemaGroup:
    json1 = _get_json_schema()
    schema = _make_group("", json1)
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
            globals()["rcsb_attributes"] = _make_schema()
        return globals()["rcsb_attributes"]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    return sorted(__all__)


__all__ = [  # noqa: F822
    "METADATA_SCHEMA_URL",
    "SEARCH_SCHEMA_URL",
    "ENV_RCSBSEARCH_DOWNLOAD_SCHEMA",
    "rcsb_attributes",
    "SchemaGroup",
]
