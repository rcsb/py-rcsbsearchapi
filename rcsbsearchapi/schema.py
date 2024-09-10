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

    def search(self, pattern: Union[str, re.Pattern], flags=0):
        """Find all attributes in the schema matching a regular expression.

        Returns:
            An iterator supplying Attr objects whose attribute matches.
        """
        matcher = re.compile(pattern, flags=flags)
        return filter(lambda a: matcher.search(a.attribute), self)

    def __iter__(self):
        """Iterate over all leaf nodes

        Example:
            >>> [a for a in attrs if "stoichiometry" in a.attribute]
            [Attr(attribute='rcsb_struct_symmetry.stoichiometry')]
        """

        def leaves(self, attr_type):
            for k, v in self.__dict__.items():
                if isinstance(v, attr_type):
                    yield v
                elif isinstance(v, SchemaGroup):
                    yield from iter(v)
                else:
                    # Shouldn't happen
                    raise TypeError(f"Unrecognized member {k!r}: {v!r}")

        return leaves(self, self.Attr)

    def __str__(self):
        return "\n".join((str(c) for c in self.__dict__.values()))


class Schema:
    def __init__(
        self,
        attr_type,
        schema_group_type,  # either "SchemaGroup" or "dict"
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
            #
            if schema_group_type == "dict":
                self.rcsb_attributes_dict = self._make_schema_dict()

            elif schema_group_type == "SchemaGroup":
                self.rcsb_attributes = self._make_schema_group()

    def _reload_schema(self, schema_url: str, schema_file: str, refetch=True, use_fallback=True):
        sD = {}
        if refetch:
            sD = self._fetch_schema(schema_url)
        if not sD and use_fallback:
            sD = self._load_json_schema(schema_file)
        return sD

    def _make_schema_group(self) -> SchemaGroup:
        schemas = [(self.struct_schema, STRUCTURE_ATTRIBUTE_SEARCH_SERVICE), (self.chem_schema, CHEMICAL_ATTRIBUTE_SEARCH_SERVICE)]
        schema = self._make_group("", schemas)
        # schema = self._set_leaves(self._make_group("", schemas))
        assert isinstance(schema, SchemaGroup)  # for type checking
        return schema

    def _make_schema_dict(self) -> dict:
        schemas = [(self.struct_schema, STRUCTURE_ATTRIBUTE_SEARCH_SERVICE, ""), (self.chem_schema, CHEMICAL_ATTRIBUTE_SEARCH_SERVICE, "")]
        schema_dict = self._make_group_dict("", schemas)
        # schema_dict = self._set_leaves(self._make_group_dict("", schemas))
        assert isinstance(schema_dict, dict)  # for type checking
        return schema_dict

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
        for node, attrtype in nodeL:
            if "anyOf" in node:
                children = {self._make_group(fullname, [(n, attrtype)]) for n in node["anyOf"]}
                # Currently only deal with anyOf in leaf nodes
                assert len(children) == 1, f"type of {fullname} couldn't be determined"
                return next(iter(children))
            if "oneOf" in node:
                children = {self._make_group(fullname, [(n, attrtype)]) for n in node["oneOf"]}
                # Currently only deal with oneOf in leaf nodes
                assert len(children) == 1, f"type of {fullname} couldn't be determined"
                return next(iter(children))
            if "allOf" in node:
                children = {self._make_group(fullname, [(n, attrtype)]) for n in node["allOf"]}
                # Currently only deal with allOf in leaf nodes
                assert len(children) == 1, f"type of {fullname} couldn't be determined"
                return next(iter(children))
            if node["type"] in ("string", "number", "integer", "date"):
                return self.Attr(fullname, attrtype)
            elif node["type"] == "array":
                # skip to items
                return self._make_group(fullname, [(node["items"], attrtype)])
            elif node["type"] == "object":
                for childname, childnode in node["properties"].items():
                    fullchildname = f"{fullname}.{childname}" if fullname else childname
                    childgroup = self._make_group(fullchildname, [(childnode, attrtype)])
                    setattr(group, childname, childgroup)
            else:
                raise TypeError(f"Unrecognized node type {node['type']!r} of {fullname}")
        return group

    def _make_group_dict(self, fullname: str, nodeL: List):
        """Represent this node of the schema as a python object

        Params:
        - name: full dot-separated attribute name

        Returns:
        An Attr (Leaf nodes) or dict (object nodes)
        """
        group = {}
        for node, attrtype, desc in nodeL:
            if "anyOf" in node:
                children = {self._make_group_dict(fullname, [(n, attrtype, n.get("description", node.get("description", desc)))]) for n in node["anyOf"]}
                # Currently only deal with anyOf in leaf nodes
                assert len(children) == 1, f"type of {fullname} couldn't be determined"
                return next(iter(children))
            if "oneOf" in node:
                children = {self._make_group_dict(fullname, [(n, attrtype, n.get("description", desc))]) for n in node["oneOf"]}
                # Currently only deal with oneOf in leaf nodes
                assert len(children) == 1, f"type of {fullname} couldn't be determined"
                return next(iter(children))
            if "allOf" in node:
                children = {self._make_group_dict(fullname, [(n, attrtype, n.get("description", desc))]) for n in node["allOf"]}
                # Currently only deal with allOf in leaf nodes
                assert len(children) == 1, f"type of {fullname} couldn't be determined"
                return next(iter(children))
            if node["type"] in ("string", "number", "integer", "date"):
                # For nodes that occur in both schemas, list of both descriptions will be passed in through desc arg
                if isinstance(desc, list):
                    return self.Attr(fullname, attrtype, desc)

                # For non-redundant nodes
                return self.Attr(fullname, attrtype, node.get("description", desc))
                # return {"attribute": fullname, "type": attrtype, "description": node.get("description", desc)}
                # return AttrLeaf(fullname, attrtype, node.get("description", ""))
            elif node["type"] == "array":
                # skip to items
                return self._make_group_dict(fullname, [(node["items"], attrtype, node.get("description", desc))])
            elif node["type"] == "object":
                for childname, childnode in node["properties"].items():
                    fullchildname = f"{fullname}.{childname}" if fullname else childname
                    # setattr(group, childname, childgroup)
                    if childname in group:
                        assert not isinstance(group[childname], dict)  # redundant name must not have nested attributes

                        # Create attrtype and description lists with existing and current value.
                        # List type triggers error if user doesn't specify service for redundant attribute.
                        currentattr = group[childname]["type"]
                        attrlist = [currentattr, attrtype]

                        currentdescript = group[childname]["description"]
                        descriptlist = [currentdescript, childnode.get("description", desc)]

                        childgroup = self._make_group_dict(fullchildname, [(childnode, attrlist, descriptlist)])
                    else:
                        childgroup = self._make_group_dict(fullchildname, [(childnode, attrtype, childnode.get("description", desc))])
                    group[childname] = childgroup
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

    def get_attribute_details(self, attribute):
        """Return attribute information given full or partial attribute name"""

        def leaves(d):
            for v in d.values():
                if "attribute" in v:
                    yield v
                else:
                    yield from leaves(v)

        split_attr = attribute.split(".")
        ptr = self.rcsb_attributes_dict
        for level in split_attr:
            if level not in ptr:
                warnings.warn(f"Attribute path segment '{level}' (for input '{attribute}') not found in schema.", UserWarning)
                return None
            ptr = ptr[level]
        if "attribute" in ptr and ptr["attribute"] == attribute:
            return ptr
        else:
            # return {(c.attribute, c.type, c.description) for c in leaves(ptr)}
            return {c for c in leaves(ptr)}

    def get_attribute_type(self, attribute):
        """Return attribute type given full attribute name"""
        split_attr = attribute.split(".")
        ptr = self.rcsb_attributes_dict
        for level in split_attr:
            if level not in ptr:
                warnings.warn(f"Attribute path segment '{level}' (for input '{attribute}') not found in schema.", UserWarning)
                return None
            ptr = ptr[level]
        if "attribute" in ptr and ptr["attribute"] == attribute:
            return ptr["type"]
        warnings.warn(f"Incomplete attribute path '{attribute}' - must specify fully-qualified path to leaf attribute node.", UserWarning)
        return None
