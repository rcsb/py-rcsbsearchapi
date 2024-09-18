"""Parse the full RCSB PDB search schema

Provides access to all valid attributes for search queries.
"""

import json
import logging
import pkgutil
import re
import warnings
from typing import List, Union
import requests
from .const import (
    STRUCTURE_ATTRIBUTE_SCHEMA_URL,
    CHEMICAL_ATTRIBUTE_SCHEMA_URL,
    STRUCTURE_ATTRIBUTE_SEARCH_SERVICE,
    STRUCTURE_ATTRIBUTE_SCHEMA_FILE,
    CHEMICAL_ATTRIBUTE_SEARCH_SERVICE,
    CHEMICAL_ATTRIBUTE_SCHEMA_FILE,
)


class SchemaGroup:
    """A non-leaf node in the RCSB PDB schema. Leaves are Attr values."""

    def __init__(self, attr_type):
        self.Attr = attr_type  # Attr or AttrLeaf
        self._members = {}  # Dictionary to store members

    def search(self, pattern: Union[str, re.Pattern], flags=0):
        """Find all attributes in the schema matching a regular expression.

        Returns:
            A list of Attr objects whose attribute matches.
        """
        matcher = re.compile(pattern, flags=flags)
        filter_match = filter(lambda a: matcher.search(a.attribute), self)
        return list(filter_match)

    def list(self):
        """Get a list of full names for all structure and chemical attributes"""
        all_list = []
        for attr in self:
            attr_dict = vars(attr)
            name = attr_dict["attribute"]
            all_list.append(name)
        return all_list

    def __iter__(self):
        """Iterate over all leaf nodes

        Example:
            >>> [a for a in attrs if "stoichiometry" in a.attribute]
            [Attr(attribute='rcsb_struct_symmetry.stoichiometry')]
        """

        def leaves(self, attr_type):
            for k, v in self._members.items():
                if isinstance(v, attr_type):
                    yield v
                elif isinstance(v, SchemaGroup):
                    yield from iter(v)
                # skips ["Attr"] key in __dict__
                elif v is attr_type:
                    continue
                else:
                    # Shouldn't happen
                    raise TypeError(f"Unrecognized member {k!r}: {v!r}")

        return leaves(self, self.Attr)

    def get_attribute_details(self, attribute: str) -> str:
        """Return attribute information given full or partial attribute name

        Args:
            attribute (str): Full attribute name
                ex: "rcsb_id", "rcsb_entity_source_organism.scientific_name"

        Returns:
            str: Return corresponding attribute description if there's a match
        """

        def leaves(d):
            for v in d.values():
                if "attribute" in v:
                    yield v
                else:
                    yield from leaves(v)

        split_attr = attribute.split(".")
        ptr = self  # dictionary of attributes
        for level in split_attr:
            if level not in ptr:
                warnings.warn(f"Attribute path segment '{level}' (for input '{attribute}') not found in schema.", UserWarning)
                return None
            ptr = ptr[level]
        if "attribute" in ptr.__dict__ and getattr(ptr, "attribute") == attribute:  # must be .__dict__ so both SchemaGroup and Attr are compared as dictionaries
            return ptr
        else:
            return {c for c in leaves(ptr)}

    def get_attribute_type(self, attribute: str) -> Union[str, None]:
        """Return attribute type given full attribute name

        Args:
            attribute (str): Full attribute name
                ex: "rcsb_id", "rcsb_entity_source_organism.scientific_name"

        Returns:
            Union[str, None]: Return search service if there's a match.
                structure search: "text"
                chemical search: "chem_text"
                both: ["text", "chem_text"] (raises error later)
        """
        split_attr = attribute.split(".")
        ptr = self  # dictionary of attributes
        for level in split_attr:
            if level not in ptr:
                warnings.warn(f"Attribute path segment '{level}' (for input '{attribute}') not found in schema.", UserWarning)
                return None
            ptr = ptr[level]
        if "attribute" in ptr.__dict__ and getattr(ptr, "attribute") == attribute:  # must be .__dict__ so both SchemaGroup and Attr are compared as dictionaries
            return getattr(ptr, "type")
        warnings.warn(f"Incomplete attribute path '{attribute}' - must specify fully-qualified path to leaf attribute node.", UserWarning)
        return None

    # Below methods are for making SchemaGroup behave as a Dict (be able to access through keys, etc).
    # This is used for automatically determining search service based on attribute name.

    def __getitem__(self, key):
        """Allow dictionary-like access to members by key."""
        return self._members[key]

    def __setitem__(self, key, value):
        """Set a member in the schema like a dictionary."""
        self._members[key] = value

    def __delitem__(self, key):
        """Delete a member from the schema like a dictionary."""
        del self._members[key]

    def __contains__(self, key):
        """Check if a member exists in the schema."""
        return key in self._members

    def keys(self):
        return self._members.keys()

    def values(self):
        return self._members.values()

    def items(self):
        return self._members.items()

    def __str__(self):
        return "\n".join(f"{key}: {value}" for key, value in self._members.items())

    def __hash__(self):
        """Make the object hashable using the hash of its members."""
        return hash(frozenset(self._members.items()))


class Schema:
    def __init__(
        self,
        attr_type,
        refetch=True,
        use_fallback=True,
        reload=True,
        struct_attr_schema_url=STRUCTURE_ATTRIBUTE_SCHEMA_URL,
        struct_attr_schema_file=STRUCTURE_ATTRIBUTE_SCHEMA_FILE,
        chem_attr_schema_url=CHEMICAL_ATTRIBUTE_SCHEMA_URL,
        chem_attr_schema_file=CHEMICAL_ATTRIBUTE_SCHEMA_FILE,
    ):
        """Initialize Schema object with all known RCSB PDB attributes.

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
        self.Attr = attr_type
        if reload:
            self.struct_schema = self._reload_schema(struct_attr_schema_url, struct_attr_schema_file, refetch, use_fallback)
            self.chem_schema = self._reload_schema(chem_attr_schema_url, chem_attr_schema_file, refetch, use_fallback)
        self.rcsb_attributes = self._make_schema_group()

    def _reload_schema(self, schema_url: str, schema_file: str, refetch=True, use_fallback=True):
        sD = {}
        if refetch:
            sD = self._fetch_schema(schema_url)
        if not sD and use_fallback:
            sD = self._load_json_schema(schema_file)
        return sD

    def _make_schema_group(self) -> SchemaGroup:
        schemas = [(self.struct_schema, STRUCTURE_ATTRIBUTE_SEARCH_SERVICE, ""), (self.chem_schema, CHEMICAL_ATTRIBUTE_SEARCH_SERVICE, "")]
        schema = self._make_group("", schemas)
        assert isinstance(schema, SchemaGroup)  # for type checking
        return schema

    def _fetch_schema(self, url: str):
        "Request the current schema from the web"
        logging.info("Requesting %s", url)
        response = requests.get(url, timeout=None)
        if response.status_code == 200:
            return response.json()
        else:
            logging.debug("HTTP response status code %r", response.status_code)
            return None

    def _load_json_schema(self, schema_file):
        logging.info("Loading attribute schema from file")
        latest = pkgutil.get_data(__package__, schema_file)
        return json.loads(latest)

    def _make_group(self, fullname: str, nodeL: List):
        """Represent this node of the schema as a python object

        Params:
        - name: full dot-separated attribute name

        Returns:
        An Attr (Leaf nodes) or SchemaGroup (object nodes)
        """
        group = SchemaGroup(self.Attr)
        for node, attrtype, desc in nodeL:
            if "anyOf" in node:
                children = {self._make_group(fullname, [(n, attrtype, n.get("description", node.get("description", desc)))]) for n in node["anyOf"]}
                # Currently only deal with anyOf in leaf nodes
                assert len(children) == 1, f"type of {fullname} couldn't be determined"
                return next(iter(children))
            if "oneOf" in node:
                children = {self._make_group(fullname, [(n, attrtype, n.get("description", desc))]) for n in node["oneOf"]}
                # Currently only deal with oneOf in leaf nodes
                assert len(children) == 1, f"type of {fullname} couldn't be determined"
                return next(iter(children))
            if "allOf" in node:
                children = {self._make_group(fullname, [(n, attrtype, n.get("description", desc))]) for n in node["allOf"]}
                # Currently only deal with allOf in leaf nodes
                assert len(children) == 1, f"type of {fullname} couldn't be determined"
                return next(iter(children))
            if node["type"] in ("string", "number", "integer", "date"):
                # For nodes that occur in both schemas, list of both descriptions will be passed in through desc arg
                if isinstance(desc, list):
                    return self.Attr(fullname, attrtype, desc)
                # For non-redundant nodes
                return self.Attr(fullname, attrtype, node.get("description", desc))
            elif node["type"] == "array":
                # skip to items
                return self._make_group(fullname, [(node["items"], attrtype, node.get("description", desc))])
            elif node["type"] == "object":
                for childname, childnode in node["properties"].items():
                    fullchildname = f"{fullname}.{childname}" if fullname else childname
                    # setattr(group, childname, childgroup)
                    if childname in group:
                        assert not isinstance(group[childname], dict)  # redundant name must not have nested attributes

                        # Create attrtype and description lists with existing and current value.
                        # List type triggers error if user doesn't specify service for redundant attribute.
                        currentattr = getattr(group[childname], "type")
                        attrlist = [currentattr, attrtype]

                        currentdescript = getattr(group[childname], "description")
                        descriptlist = [currentdescript, childnode.get("description", desc)]

                        childgroup = self._make_group(fullchildname, [(childnode, attrlist, descriptlist)])
                    else:
                        childgroup = self._make_group(fullchildname, [(childnode, attrtype, childnode.get("description", desc))])
                    # adding to SchemaGroup as a dict allows for determining search service by attribute name with O(1) lookup
                    group[childname] = childgroup

                    # adding to SchemaGroup as an attribute allows for tab-completion for rcsb_attributes/attrs
                    setattr(group, childname, childgroup)
            else:
                raise TypeError(f"Unrecognized node type {node['type']!r} of {fullname}")
        return group

    def _set_leaves(self, d: dict) -> dict:
        """Converts Attr objects to dictionary format."""
        for leaf in d:
            if isinstance(d[leaf], self.Attr):
                d[leaf] = d[leaf].__dict__
            else:
                d[leaf] = self._set_leaves(d[leaf])
        return d
