"""Interact with the [RCSB PDB Search API](https://search.rcsb.org/#search-api).
"""

from __future__ import annotations
import functools
import json
import logging
import math
import sys
import urllib.parse
import uuid
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    overload,
)

import requests
from .const import STRUCTURE_ATTRIBUTE_SEARCH_SERVICE, REQUESTS_PER_SECOND, FULL_TEXT_SEARCH_SERVICE, SEQUENCE_SEARCH_SERVICE, SEQUENCE_SEARCH_MIN_NUM_OF_RESIDUES
from .const import RCSB_SEARCH_API_QUERY_URL, SEQMOTIF_SEARCH_SERVICE, SEQMOTIF_SEARCH_MIN_CHARACTERS, UPLOAD_URL, RETURN_UP_URL, STRUCT_SIM_SEARCH_SERVICE
from .const import STRUCTMOTIF_SEARCH_SERVICE, STRUCT_MOTIF_MIN_RESIDUES, STRUCT_MOTIF_MAX_RESIDUES, CHEM_SIM_SEARCH_SERVICE
from .schema import Schema

if sys.version_info > (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

# tqdm is optional
# Allowed return types for searches. https://search.rcsb.org/#return-type
ReturnType = Literal["entry", "assembly", "polymer_entity", "non_polymer_entity", "polymer_instance", "mol_definition"]
ReturnContentType = Literal["experimental", "computational"]  # results_content_type parameter list values
SequenceType = Literal["dna", "rna", "protein"]  # possible sequence types for sequence searching
SeqMode = Literal["simple", "prosite", "regex"]  # possible sequence motif formats
StructEntryType = Literal["entry_id", "file_url", "file_upload"]  # possible entry types for structure similarity search
StructSimInputType = Literal["assembly_id", "chain_id"]  # Possible ID choices for structure similarity search
StructSimSearchSpace = Literal["polymer_entity_instance", "assembly"]  # target search spaces for structure similarity searchf
StructSimOperator = Literal["strict_shape_match", "relaxed_shape_match"]  # possible operators for structure similarity searchf
StructMotifExchanges = Literal[
    "ALA",
    "CYS",
    "ASP",
    "GLU",
    "PHE",
    "GLY",
    "HIS",
    "ILE",
    "LYS",
    "LEU",
    "MET",
    "ASN",
    "PYL",
    "PRO",
    "GLN",
    "ARG",
    "SER",
    "THR",
    "SEC",
    "VAL",
    "TRP",
    "TYR",
    "DA",
    "DC",
    "DG",
    "DI",
    "DT",
    "DU",
    "A",
    "C",
    "G",
    "I",
    "U",
    "UNK",
    "N",
]
StructMotifTolerance = Literal[0, 1, 2, 3]
StructMotifAtomPairing = Literal["ALL", "BACKBONE", "SIDE_CHAIN", "PSEUDO_ATOMS"]
StructMotifPruning = Literal["NONE", "KRUSKAL"]
SubsetDescriptorType = Literal["InChI", "SMILES"]  # possible subset matching or descriptor types parameters for chemical similarity search
ChemSimType = Literal["formula", "descriptor"]  # possible query types for chemical similarity search
ChemSimMatchType = Literal[
    "graph-relaxed-stereo",
    "graph-relaxed",
    "fingerprint-similarity",  # possible match types for descriptor query type (Chemical similarity search)
    "sub-struct-graph-relaxed-stereo",
    "sub-struct-graph-relaxed",
    "graph-exact",
]
TAndOr = Literal["and", "or"]
VerbosityLevel = Literal["compact", "minimal", "verbose"]
AggregationType = Literal["terms", "histogram", "date_histogram", "range", "date_range", "cardinality"]
# All valid types for Terminal values
TValue = Union[
    str,
    int,
    float,
    date,
    List[str],
    List[int],
    List[float],
    List[date],
    Tuple[str, ...],
    Tuple[int, ...],
    Tuple[float, ...],
    Tuple[date, ...],
    Dict[str, Any],
]
# Types valid for numeric operators
TNumberLike = Union[int, float, date, "Value[int]", "Value[float]", "Value[date]"]


def fileUpload(filepath: str, fmt: str = "cif") -> str:
    """Take a file given by a filepath, and return the
    corresponding URL to use in a structure search. This URL
    should then be passed through as part of the value parameter,
    along with the format of the file."""
    x = open(filepath, mode="rb")
    res = requests.post(UPLOAD_URL, files={"file": x, "format": fmt}, timeout=None)
    try:
        spec = res.json()["key"]
    except KeyError:
        raise TypeError("There was an issue processing the file. Check the file format.")
    return RETURN_UP_URL + spec


class Query(ABC):
    """Base class for all types of queries.

    Queries can be combined using set operators:

    - `q1 & q2`: Intersection (AND)
    - `q1 | q2`: Union (OR)
    - `~q1`: Negation (NOT)
    - `q1 - q2`: Difference (implemented as `q1 & ~q2`)
    - `q1 ^ q2`: Symmetric difference (XOR, implemented as `(q1 & ~q2) | (~q1 & q2)`)

    Note that only AND, OR, and negation of terminals are directly supported by
    the API, so other operations may be slower.

    Queries can be executed by calling them as functions (`list(query())`) or using
    the exec function.

    Queries are immutable, and all modifying functions return new instances.
    """

    @abstractmethod
    def to_dict(self) -> Dict:
        """Get dictionary representing this query"""

    def to_json(self) -> str:
        """Get JSON string of this query"""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @abstractmethod
    def _assign_ids(self, node_id=0) -> Tuple["Query", int]:
        """Assign node_ids sequentially for all terminal nodes

        This is a helper for the :py:meth:`Query.assign_ids` method

        Args:
            node_id: Id to assign to the first leaf of this query

        Returns:
            query: The modified query, with node_ids assigned
            node_id: The next available node_id

        """

    def assign_ids(self) -> "Query":
        """Assign node_ids sequentially for all terminal nodes

        Returns:
            the modified query, with node_ids assigned sequentially from 0
        """
        return self._assign_ids(0)[0]

    @abstractmethod
    def __invert__(self) -> "Query":
        """Negation: `~a`"""

    def __and__(self, other: "Query") -> "Query":
        """Intersection: `a & b`"""
        assert isinstance(other, Query)
        return Group("and", [self, other])

    def __or__(self, other: "Query") -> "Query":
        """Union: `a | b`"""
        assert isinstance(other, Query)
        return Group("or", [self, other])

    def __sub__(self, other: "Query") -> "Query":
        """Difference: `a - b`"""
        return self & ~other

    def __xor__(self, other: "Query") -> "Query":
        """Symmetric difference: `a ^ b`"""
        return (self & ~other) | (~self & other)

    def exec(
        self, return_type: ReturnType = "entry", rows: int = 10000, return_content_type: List[ReturnContentType] = ["experimental"], results_verbosity: VerbosityLevel = "compact"
    ) -> "Session":
        # pylint: disable=dangerous-default-value
        """Evaluate this query and return an iterator of all result IDs"""
        return Session(self, return_type, rows, return_content_type, results_verbosity)

    def __call__(
        self, return_type: ReturnType = "entry", rows: int = 10000, return_content_type: List[ReturnContentType] = ["experimental"], results_verbosity: VerbosityLevel = "compact"
    ) -> "Session":
        # pylint: disable=dangerous-default-value
        """Evaluate this query and return an iterator of all result IDs"""
        return self.exec(return_type, rows, return_content_type, results_verbosity)

    def count(self, return_type: ReturnType = "entry", return_content_type: List[ReturnContentType] = ["experimental"]) -> int:
        # pylint: disable=dangerous-default-value
        """Get the number of results found by this query"""
        s = Session(self, return_type, 0, return_content_type)
        response = s._single_query()
        return response["total_count"] if response else 0

    def facets(self, return_type: ReturnType = "entry", facets: Union["Facet", "FilterFacet", List[Union["Facet", "FilterFacet"]]] = None) -> List:
        """Perform a facets query and return the buckets"""
        s = Session(self, return_type=return_type, rows=0, facets=facets)
        response = s._single_query()
        return response["facets"] if response else []

    @overload
    def and_(self, other: "Query") -> "Query":
        ...

    @overload
    def and_(self, other: Union[str, "Attr"]) -> "PartialQuery":
        ...

    def and_(self, other: Union[str, "Query", "Attr"], qtype=STRUCTURE_ATTRIBUTE_SEARCH_SERVICE) -> Union["Query", "PartialQuery"]:
        """Extend this query with an additional attribute via an AND"""
        if isinstance(other, Query):
            return self & other
        elif isinstance(other, Attr):
            return PartialQuery(self, "and", other)
        elif isinstance(other, str):
            return PartialQuery(self, "and", Attr(other, qtype))
        else:
            raise TypeError(f"Expected Query or Attr, got {type(other)}")

    @overload
    def or_(self, other: "Query") -> "Query":
        ...

    @overload
    def or_(self, other: Union[str, "Attr"]) -> "PartialQuery":
        ...

    def or_(self, other: Union[str, "Query", "Attr"], qtype=STRUCTURE_ATTRIBUTE_SEARCH_SERVICE) -> Union["Query", "PartialQuery"]:
        """Extend this query with an additional attribute via an OR"""
        if isinstance(other, Query):
            return self | other
        elif isinstance(other, Attr):
            return PartialQuery(self, "or", other)
        elif isinstance(other, str):
            return PartialQuery(self, "or", Attr(other, qtype))
        else:
            raise TypeError(f"Expected Query or Attr, got {type(other)}")


@dataclass(frozen=True)
class Terminal(Query):
    """A terminal query node.

    Used for doing various types of searches. Accepts a service type and a dictionary of parameters.
    The set of parameters differs for different search services.

    Terminal can be built by passing in a service and parameter dictionary, but it's tedious work.
    Typically, it's built by child classes that each represent a unique type of search.
    This allows for more concise searching.

    Examples:
        >>> Terminal("full_text", {"value": "protease"})
        >>> Terminal("text", {"attribute": "rcsb_id", "operator": "in", "negation": False, "value": ["5T89, "1TIM"]})
    """

    service: Union[List, str]
    params: Dict[str, Any]
    node_id: int = 0

    def to_dict(self):
        return dict(
            type="terminal",
            service=self.service,
            parameters=self.params,
            node_id=self.node_id,
        )

    def __invert__(self):
        if isinstance(self, AttributeQuery):
            return AttributeQuery(attribute=self.params.get("attribute"), operator=self.params.get("operator"), negation=not self.params.get("negation"), value=self.params.get("value"))
        else:
            raise TypeError("Negation is not supported by type " + str(type(self)))  # Attribute Queries are the only query type to support inversion.

    def _assign_ids(self, node_id=0) -> Tuple[Query, int]:
        if self.node_id == node_id:
            return (self, node_id + 1)
        else:
            return (
                Terminal(self.service, self.params, node_id),
                node_id + 1,
            )

    # def __str__(self): (leaving it commented out to find out what it actually does once something breaks)
    #     """Return a simplified string representation

    #     Example:
    #         >>> Terminal(service="serv", params="par")

    #     """
    #     return f"Terminal(service={self.service!r}, params={self.params!r})"


@dataclass(frozen=True)
class Attr:
    """A search attribute, e.g. "rcsb_entry_container_identifiers.entry_id"

    Terminals can be constructed from Attr objects using either a functional syntax,
    which mirrors the API operators, or with python operators.

    +--------------------+---------------------+
    | Fluent Function    | Operator            |
    +====================+=====================+
    | exact_match        | attr == str         |
    +--------------------+---------------------+
    | contains_words     |                     |
    +--------------------+---------------------+
    | contains_phrase    |                     |
    +--------------------+---------------------+
    | greater            | attr > date,number  |
    +--------------------+---------------------+
    | less               | attr < date,number  |
    +--------------------+---------------------+
    | greater_or_equal   | attr >= date,number |
    +--------------------+---------------------+
    | less_or_equal      | attr <= date,number |
    +--------------------+---------------------+
    | equals             | attr == date,number |
    +--------------------+---------------------+
    | range              | dict (keys below)*  |
    +--------------------+---------------------+
    | exists             | bool(attr)          |
    +--------------------+---------------------+
    | in\\_              |                     |
    +--------------------+---------------------+

    Rather than their normal bool return values, operators return Terminals.

    Pre-instantiated attributes are available from the
    :py:data:`rcsbsearchapi.rcsb_attributes` object. These are generally easier to use
    than constructing Attr objects by hand. A complete list of valid attributes is
    available in the `schema <https://search.rcsb.org/rcsbsearch/v2/metadata/schema>`_.

    * The `range` dictionary requires the following keys:
     * "from" -> int
     * "to" -> int
     * "include_lower" -> bool
     * "include_upper" -> bool
    """

    attribute: str
    type: Optional[Union[List, str]] = None
    description: Optional[Union[str, List[str]]] = None

    def exact_match(self, value: Union[str, "Value[str]"]) -> "AttributeQuery":
        """Exact match with the value"""
        if isinstance(value, Value):
            value = value.value
        return AttributeQuery(self.attribute, "exact_match", value, self.type)

    def contains_words(self, value: Union[str, "Value[str]", List[str], "Value[List[str]]"]) -> "AttributeQuery":
        """Match any word within the string.

        Words are split at whitespace. All results which match any word are returned,
        with results matching more words sorted first.
        """
        if isinstance(value, Value):
            value = value.value
        if isinstance(value, list):
            value = " ".join(value)
        return AttributeQuery(self.attribute, "contains_words", value, self.type)

    def contains_phrase(self, value: Union[str, "Value[str]"]) -> "AttributeQuery":
        """Match an exact phrase"""
        if isinstance(value, Value):
            value = value.value
        return AttributeQuery(self.attribute, "contains_phrase", value, self.type)

    def greater(self, value: TNumberLike) -> "AttributeQuery":
        """Attribute > `value`"""
        if isinstance(value, Value):
            value = value.value
        return AttributeQuery(self.attribute, "greater", value, self.type)

    def less(self, value: TNumberLike) -> "AttributeQuery":
        """Attribute < `value`"""
        if isinstance(value, Value):
            value = value.value
        return AttributeQuery(self.attribute, "less", value, self.type)

    def greater_or_equal(self, value: TNumberLike) -> "AttributeQuery":
        """Attribute >= `value`"""
        if isinstance(value, Value):
            value = value.value
        return AttributeQuery(self.attribute, "greater_or_equal", value, self.type)

    def less_or_equal(self, value: TNumberLike) -> "AttributeQuery":
        """Attribute <= `value`"""
        if isinstance(value, Value):
            value = value.value
        return AttributeQuery(self.attribute, "less_or_equal", value, self.type)

    def equals(self, value: TNumberLike) -> "AttributeQuery":
        """Attribute == `value`"""
        if isinstance(value, Value):
            value = value.value
        return AttributeQuery(self.attribute, "equals", value, self.type)

    def range(self, value: Dict[str, Any]) -> "AttributeQuery":
        """Attribute is within the specified half-open range

        Args:
            value: lower and upper bounds `[a, b)`
        """
        if isinstance(value, Value):
            value = value.value
        return AttributeQuery(self.attribute, "range", value, self.type)

    def exists(self) -> AttributeQuery:
        """Attribute is defined for the structure"""
        return AttributeQuery(self.attribute, operator="exists")

    def in_(
        self,
        value: Union[
            List[str],
            List[int],
            List[float],
            List[date],
            Tuple[str, ...],
            Tuple[int, ...],
            Tuple[float, ...],
            Tuple[date, ...],
            "Value[List[str]]",
            "Value[List[int]]",
            "Value[List[float]]",
            "Value[List[date]]",
            "Value[Tuple[str, ...]]",
            "Value[Tuple[int, ...]]",
            "Value[Tuple[float, ...]]",
            "Value[Tuple[date, ...]]",
        ],
    ) -> "AttributeQuery":
        """Attribute is contained in the list of values"""
        if isinstance(value, Value):
            value = value.value
        return AttributeQuery(self.attribute, operator="in", value=value)

    # Need ignore[override] because typeshed restricts __eq__ return value
    # https://github.com/python/mypy/issues/2783
    @overload  # type: ignore[override]
    def __eq__(self, value: "Attr") -> bool:
        ...

    @overload  # type: ignore[override]
    def __eq__(
        self,
        value: Union[
            str,
            int,
            float,
            date,
            "Value[str]",
            "Value[int]",
            "Value[float]",
            "Value[date]",
        ],
    ) -> Terminal:
        ...

    def __eq__(
        self,
        value: Union[
            "Attr",
            str,
            int,
            float,
            date,
            "Value[str]",
            "Value[int]",
            "Value[float]",
            "Value[date]",
        ],
    ) -> Union[Terminal, bool]:  # type: ignore[override]
        if isinstance(value, Attr):
            return self.attribute == value.attribute
        if isinstance(value, Value):
            value = value.value
        if isinstance(value, str):
            return self.exact_match(value)
        elif isinstance(value, date) or isinstance(value, float) or isinstance(value, int):
            return self.equals(value)
        else:
            return NotImplemented

    @overload  # type: ignore[override]
    def __ne__(self, value: "Attr") -> bool:
        ...

    @overload  # type: ignore[override]
    def __ne__(
        self,
        value: Union[
            str,
            int,
            float,
            date,
            "Value[str]",
            "Value[int]",
            "Value[float]",
            "Value[date]",
        ],
    ) -> Terminal:
        ...

    def __ne__(
        self,
        value: Union[
            "Attr",
            str,
            int,
            float,
            date,
            "Value[str]",
            "Value[int]",
            "Value[float]",
            "Value[date]",
        ],
    ) -> Union[Terminal, bool]:  # type: ignore[override]
        if isinstance(value, Attr):
            return self.attribute != value.attribute
        if isinstance(value, Value):
            value = value.value
        return ~(self == value)

    def __lt__(self, value: TNumberLike) -> Terminal:
        if isinstance(value, Value):
            value = value.value
        return self.less(value)

    def __le__(self, value: TNumberLike) -> Terminal:
        if isinstance(value, Value):
            value = value.value
        return self.less_or_equal(value)

    def __gt__(self, value: TNumberLike) -> Terminal:
        if isinstance(value, Value):
            value = value.value
        return self.greater(value)

    def __ge__(self, value: TNumberLike) -> Terminal:
        if isinstance(value, Value):
            value = value.value
        return self.greater_or_equal(value)

    def __bool__(self) -> Terminal:  # pylint: disable=invalid-bool-returned
        return self.exists()

    def __contains__(self, value: Union[str, List[str], "Value[str]", "Value[List[str]]"]) -> Terminal:
        """Maps to contains_words or contains_phrase depending on the value passed.

        * `"value" in attr` maps to `attr.contains_phrase("value")` for simple values.
        * `["value"] in attr` maps to `attr.contains_words(["value"])` for lists and
          tuples.
        """
        if isinstance(value, Value):
            value = value.value
        if isinstance(value, list):
            if len(value) == 0 or isinstance(value[0], str):
                return self.contains_words(value)
            else:
                return NotImplemented
        else:
            return self.contains_phrase(value)


@dataclass(frozen=True)
class AttrLeaf:
    attribute: str
    type: Union[str, List]
    description: Union[str, List]

    def __contains__(self, key):
        return key in self.__dict__

    def __getitem__(self, key):
        if key in self.__dict__:
            return self.__dict__[key]
        raise KeyError(f"'{key}' not found in object")


SCHEMA = Schema(Attr, "SchemaGroup")


class AttributeQuery(Terminal):
    """Special case of a Terminal for Structure and Chemical Attribute Searches

    AttributeQueries compares some *attribute* of a structure to a value.

    Examples:
        >>> AttributeQuery("exptl.method", "exact_match", "X-RAY DIFFRACTION")
        >>> AttributeQuery("rcsb_entry_container_identifiers.entry_id", operator="in", value=["4HHB", "2GS2"])

    A full list of attributes is available in the
    `schema <https://search.rcsb.org/rcsbsearch/v2/metadata/schema>`_.
    Operators are documented `here <https://search.rcsb.org/#field-queries>`_.

    The :py:class:`Attr` class provides a more pythonic way of constructing AttributeQueries.
    """

    def __init__(
        self,
        attribute: str = None,
        operator: str = None,
        value: Optional[TValue] = None,
        service: Optional[str] = None,
        negation: Optional[bool] = False,
    ):
        """Search for the string value given possible attribute or operator
        Also can specify service and negation

        Args:
            attribute: specify attribute for search (i.e struct.title, exptl.method, rcsb_id)
            operator: specify operation to be done for search (i.e "contains_phrase", "exact_match")
            value: text query
            service: specify what search service (i.e "text", "text_chem")
            negation: logical not
        """
        paramsD = {"attribute": attribute, "operator": operator, "negation": negation}

        if value is not None:
            paramsD.update({"value": value})
        if not service:
            service = SCHEMA.rcsb_attributes.get_attribute_type(attribute)

        if isinstance(service, list):
            error_msg = ""
            for serv in service:
                error_msg += f'  AttributeQuery(attribute="{attribute}", operator="{operator}", value="{value}", service="{serv}")\n'
            raise ValueError(
                f'"{attribute}" is in both structure and chemical attributes. Construct an AttributeQuery and specify search service.\n'
                + f"{error_msg}"
            )
        assert isinstance(service, str)
        super().__init__(params=paramsD, service=service)


class TextQuery(Terminal):
    """Special case of a Terminal for free-text queries"""

    def __init__(self, value: str):
        """Search for the string value anywhere in the text

        Args:
            value: free-text query
        """
        super().__init__(service=FULL_TEXT_SEARCH_SERVICE, params={"value": value})


class SequenceQuery(Terminal):
    """Special case of a terminal for protein, DNA, or RNA sequence queries"""

    def __init__(self, value: str, evalue_cutoff: Optional[float] = 0.1, identity_cutoff: Optional[float] = 0, sequence_type: Optional[SequenceType] = "protein"):
        """The string value is a target sequence that is searched
        Args:
            value: sequence query
        """
        if len(value) < SEQUENCE_SEARCH_MIN_NUM_OF_RESIDUES:  # (placeholder for now) look into deriving constraints from API Schema programatically
            raise ValueError("The sequence must contain at least 25 residues")
        if identity_cutoff < 0.0 or identity_cutoff > 1.0:
            raise ValueError("Identity cutoff should be between 0 and 1 (inclusive)")
        else:
            super().__init__(
                service=SEQUENCE_SEARCH_SERVICE, params={"evalue_cutoff": evalue_cutoff, "identity_cutoff": identity_cutoff, "sequence_type": sequence_type, "value": value}
            )


class SeqMotifQuery(Terminal):
    """Special case of a terminal for protein, DNA, or RNA sequence motif queries"""

    def __init__(self, value: str, pattern_type: Optional[SeqMode] = "simple", sequence_type: Optional[SequenceType] = "protein"):
        if len(value) < SEQMOTIF_SEARCH_MIN_CHARACTERS:
            raise ValueError("The sequence motif must contain at least 2 characters")
        else:
            super().__init__(service=SEQMOTIF_SEARCH_SERVICE, params={"value": value, "pattern_type": pattern_type, "sequence_type": sequence_type})


class StructSimilarityQuery(Terminal):
    """Special case of a terminal for structure similarity queries"""

    def __init__(
        self,
        structure_search_type: StructEntryType = "entry_id",
        entry_id: Optional[str] = None,
        file_url: Optional[str] = None,
        file_path: Optional[str] = None,
        structure_input_type: Optional[StructSimInputType] = "assembly_id",
        assembly_id: Optional[str] = "1",
        chain_id: Optional[str] = None,
        operator: StructSimOperator = "strict_shape_match",
        target_search_space: StructSimSearchSpace = "assembly",
        file_format: Optional[str] = None,
    ):

        parameters = {"operator": operator, "target_search_space": target_search_space}

        if structure_search_type == "entry_id":
            if structure_input_type == "assembly_id":
                parameters["value"] = {"entry_id": entry_id, "assembly_id": assembly_id}
            elif structure_input_type == "chain_id":
                parameters["value"] = {"entry_id": entry_id, "asym_id": chain_id}

        elif structure_search_type == "file_url":
            parameters["value"] = {"url": file_url, "format": file_format}

        elif structure_search_type == "file_upload":
            parameters["value"] = {"url": fileUpload(file_path, file_format), "format": "bcif"}

        super().__init__(service=STRUCT_SIM_SEARCH_SERVICE, params=parameters)


class StructureMotifResidue:
    """This class is for defining residues. For use with the Structure Motif Search."""

    def __init__(
        self,
        chain_id: Optional[str] = None,
        struct_oper_id: Optional[str] = None,
        label_seq_id: Optional[str] = None,
        exchanges: Optional[list] = None,  # List of StructMotifExchanges objects
    ):
        assert chain_id, "You must provide a chain_id."
        assert struct_oper_id, "You must provide a struct_oper_id."
        assert label_seq_id, "You must provide a label_seq_id. "
        self.label_asym = chain_id
        self.struct_oper_id = struct_oper_id
        self.label_seq_id = label_seq_id

        if exchanges:
            assert len(exchanges) <= 4, "No more than 4 allowed residues can be specified in an individual residue"
            self.exchanges = exchanges
        else:
            self.exchanges = None

    def to_dict(self):
        return {"label_asym_id": self.label_asym, "struct_oper_id": self.struct_oper_id, "label_seq_id": self.label_seq_id}


class StructMotifQuery(Terminal):
    """Special case of a terminal for structure motif queries.

    If you provide an entry_id, the other optional parameters can be ignored.
    If you provide a file_url, you must also provide a file_extension.
    If you provide a filepath, you must also provide a file_extension.

    As is standard with Structure Motif Queries, you must include a list of residues.

    Positional arguments STRONGLY discouraged."""

    def __init__(
        self,
        structure_search_type: StructEntryType = "entry_id",
        backbone_distance_tolerance: StructMotifTolerance = 1,
        side_chain_distance_tolerance: StructMotifTolerance = 1,
        angle_tolerance: StructMotifTolerance = 1,
        entry_id: Optional[str] = None,
        url: Optional[str] = None,
        file_path: Optional[str] = None,
        file_extension: Optional[str] = None,
        residue_ids: Optional[list] = None,  # List of StructureMotifResidue objects
        rmsd_cutoff: int = 2,
        atom_pairing_scheme: StructMotifAtomPairing = "SIDE_CHAIN",
        motif_pruning_strategy: StructMotifPruning = "KRUSKAL",
        allowed_structures: Optional[list] = None,  # List of strings
        excluded_structures: Optional[list] = None,  # List of strings
        limit: Optional[int] = None,
    ):
        # we will construct value, and then pass it through. That's like 95% of this lol
        if not residue_ids:
            raise ValueError("You must include residues in a Structure Motif Query")
        if len(residue_ids) > STRUCT_MOTIF_MAX_RESIDUES or len(residue_ids) < STRUCT_MOTIF_MIN_RESIDUES:
            raise ValueError("A Structure Motif Query Must contain 2-10 residues.")
        value = {}
        if structure_search_type == "entry_id":
            assert entry_id and isinstance(entry_id, str), "You must provide a valid entry_id for an entry_id query"
            value["entry_id"] = entry_id
        elif structure_search_type == "file_url":
            assert url and isinstance(url, str), "You must provide a url for a file_url query"
            assert file_extension and isinstance(file_extension, str), "you must provide a valid file extension"
            value["url"] = url
            value["format"] = file_extension
        elif structure_search_type == "file_upload":
            assert file_path and isinstance(file_path, str), "you must provide a valid filepath"
            assert file_extension and isinstance(file_extension, str), "you must provide a valid file_extension"
            value["url"] = fileUpload(file_path, file_extension)
            value["format"] = "bcif"
        else:
            raise ValueError("Invalid Query Type Provided")
        residue_id_dicts = []
        exchanges = []
        total_res = 0
        for x in residue_ids:
            residue_id_dicts.append(x.to_dict())
            if x.exchanges:
                exchanges.append({"residue_id": x.to_dict(), "allowed": x.exchanges})
                total_res += len(x.exchanges)
                assert total_res <= 16, "No more than 16 allowed exchanges total per query, regardless of residue count."
        value["residue_ids"] = residue_id_dicts

        # assemble params. This is done differently from before because so many of these are optional here,
        # and I'm not aware of a method to make inclusions be skipped if a value is NONE when
        # declaring values on instantiation.

        params = {
            "value": value,
            "backbone_distance_tolerance": backbone_distance_tolerance,
            "side_chain_distance_tolerance": side_chain_distance_tolerance,
            "angle_tolerance": angle_tolerance,
            "rmsd_cutoff": rmsd_cutoff,
            "atom_pairing_scheme": atom_pairing_scheme,
            "motif_pruning_strategy": motif_pruning_strategy,
        }
        if allowed_structures:
            params["allowed_structures"] = allowed_structures
        if excluded_structures:
            params["excluded_structures"] = excluded_structures
        if exchanges:
            params["exchanges"] = exchanges
        if limit:
            params["limit"] = limit

        # now call super

        super().__init__(service=STRUCTMOTIF_SEARCH_SERVICE, params=params)


class ChemSimilarityQuery(Terminal):
    """Special case of Terminal for chemical similarity search queries"""

    def __init__(
        self,
        value: Optional[str] = None,
        query_type: ChemSimType = "formula",
        match_subset: Optional[bool] = False,
        descriptor_type: Optional[SubsetDescriptorType] = None,
        match_type: Optional[ChemSimMatchType] = None,
    ):
        """Guide for "descriptor_type" options:
        +-------------------------------------------+-----------------------------------+
        | Match Type                                | descriptor_type                   |
        +===========================================+===================================+
          Similar Ligands (Stereospecific)          | "graph-relaxed-stereo"
          Similar Ligands (including Stereoisomers) | "graph-relaxed"
          Similar Ligands (Quick screen)            | "fingerprint-similarity"
          Substructure (Stereospecific)             | "sub-struct-graph-relaxed-stereo"
          Substructure (including Stereoisomers)    | "sub-struct-graph-relaxed"
          Exact match                               | "graph-exact"
        +-------------------------------------------+-----------------------------------+
        """

        parameters = {"value": value, "type": query_type}

        if query_type == "formula":
            parameters["match_subset"] = match_subset

        elif query_type == "descriptor":
            parameters["descriptor_type"] = descriptor_type
            parameters["match_type"] = match_type

        super().__init__(service=CHEM_SIM_SEARCH_SERVICE, params=parameters)


@dataclass(frozen=True)
class Group(Query):
    """AND and OR combinations of queries"""

    operator: TAndOr
    nodes: Iterable[Query] = ()

    def to_dict(self):
        return dict(
            type="group",
            logical_operator=self.operator,
            nodes=[node.to_dict() for node in self.nodes],
        )

    def __invert__(self):
        if self.operator == "and":
            return Group("or", [~node for node in self.nodes])

    def __and__(self, other: Query) -> Query:
        # Combine nodes if possible
        if self.operator == "and":
            if isinstance(other, Group):
                if other.operator == "and":
                    return Group("and", (*self.nodes, *other.nodes))
            elif isinstance(other, Query):
                return Group("and", (*self.nodes, other))
            else:
                return NotImplemented

        return super().__and__(other)

    def __or__(self, other: Query) -> Query:
        # Combine nodes if possible
        if self.operator == "or":
            if isinstance(other, Group):
                if other.operator == "or":
                    return Group("or", (*self.nodes, *other.nodes))
            elif isinstance(other, Query):
                return Group("or", (*self.nodes, other))
            else:
                return NotImplemented

        return super().__or__(other)

    def _assign_ids(self, node_id=0) -> Tuple[Query, int]:
        nodes = []
        changed = False
        for node in self.nodes:
            assigned = node._assign_ids(node_id)
            nodes.append(assigned[0])
            node_id = assigned[1]
            # Track whether any nodes were modified
            changed = changed or assigned[0] is node
        if changed:
            return (Group(self.operator, nodes), node_id)
        else:
            return (self, node_id)

    def __str__(self):
        """"""  # hide in documentation
        if self.operator == "and":
            return f"({' & '.join((str(n) for n in self.nodes))})"
        elif self.operator == "or":
            return f"({' | '.join((str(n) for n in self.nodes))})"
        else:
            raise ValueError("Illegal Operator")


# Type for functions returning Terminal
FTerminal = TypeVar("FTerminal", bound=Callable[..., Terminal])
# Type for functions returning Query
FQuery = TypeVar("FQuery", bound=Callable[..., Query])


def _attr_delegate(attr_func: FTerminal) -> Callable[[FQuery], FQuery]:
    """Decorator for PartialQuery methods. Delegates a function to self.attr.

    This reduces boilerplate, especially for classes with lots of dunder methods
    (preventing the use of `__getattr__`).

    Argument:
    - attr_func: A method in the Attr class producing a Terminal

    Returns: A function producing a Query according to the PartialQuery's operator
    """

    def decorator(partialquery_func: FQuery):
        @functools.wraps(partialquery_func)
        def wrap(self: "PartialQuery", *args, **kwargs) -> Query:
            term: Terminal = attr_func(self.attr, *args, **kwargs)
            if self.operator == "and":
                return self.query & term
            elif self.operator == "or":
                return self.query | term
            else:
                raise ValueError(f"Unknown operator: {self.operator}")

        return wrap

    return decorator


class PartialQuery:
    """A PartialQuery extends a growing query with an Attr. It is constructed
    using the fluent syntax with the `and_` and `or_` methods. It is not usually
    necessary to create instances of this class directly.

    PartialQuery instances behave like Attr instances in most situations.
    """

    attr: Attr
    query: Query
    operator: TAndOr

    def __init__(self, query: Query, operator: TAndOr, attr: Attr):
        self.query = query
        self.operator = operator
        self.attr = attr

    @_attr_delegate(Attr.exact_match)
    def exact_match(self, value: Union[str, "Value[str]"]) -> Query:
        ...

    @_attr_delegate(Attr.contains_words)
    def contains_words(self, value: Union[str, "Value[str]", List[str], "Value[List[str]]"]) -> Query:
        ...

    @_attr_delegate(Attr.contains_phrase)
    def contains_phrase(self, value: Union[str, "Value[str]"]) -> Query:
        ...

    @_attr_delegate(Attr.greater)
    def greater(self, value: TNumberLike) -> Query:
        ...

    @_attr_delegate(Attr.less)
    def less(self, value: TNumberLike) -> Query:
        ...

    @_attr_delegate(Attr.greater_or_equal)
    def greater_or_equal(self, value: TNumberLike) -> Query:
        ...

    @_attr_delegate(Attr.less_or_equal)
    def less_or_equal(self, value: TNumberLike) -> Query:
        ...

    @_attr_delegate(Attr.equals)
    def equals(self, value: TNumberLike) -> Query:
        ...

    @_attr_delegate(Attr.range)
    def range(self, value: Dict[str, Any]) -> Query:
        ...

    @_attr_delegate(Attr.exists)
    def exists(self) -> Query:
        ...

    @_attr_delegate(Attr.in_)
    def in_(
        self,
        value: Union[
            str,
            int,
            float,
            date,
            "Value[str]",
            "Value[int]",
            "Value[float]",
            "Value[date]",
        ],
    ) -> Query:
        ...

    @overload  # type: ignore[override]
    def __eq__(self, value: "PartialQuery") -> bool:
        ...

    @overload  # type: ignore[override]
    def __eq__(
        self,
        value: Union[
            str,
            int,
            float,
            date,
            "Value[str]",
            "Value[int]",
            "Value[float]",
            "Value[date]",
        ],
    ) -> Query:
        ...

    def __eq__(
        self,
        value: Union[
            "PartialQuery",
            str,
            int,
            float,
            date,
            "Value[str]",
            "Value[int]",
            "Value[float]",
            "Value[date]",
        ],
    ) -> Union[Query, bool]:  # type: ignore[override]
        if isinstance(value, PartialQuery):
            return self.attr == value.attr and self.query == value.query and self.operator == value.operator

        if self.operator == "and":
            return self.query & (self.attr == value)
        elif self.operator == "or":
            return self.query | (self.attr == value)
        else:
            raise ValueError(f"Unknown operator: {self.operator}")

    @overload  # type: ignore[override]
    def __ne__(self, value: "PartialQuery") -> bool:
        ...

    @overload  # type: ignore[override]
    def __ne__(
        self,
        value: Union[
            str,
            int,
            float,
            date,
            "Value[str]",
            "Value[int]",
            "Value[float]",
            "Value[date]",
        ],
    ) -> Query:
        ...

    def __ne__(
        self,
        value: Union[
            "PartialQuery",
            str,
            int,
            float,
            date,
            "Value[str]",
            "Value[int]",
            "Value[float]",
            "Value[date]",
        ],
    ) -> Union[Query, bool]:  # type: ignore[override]
        if isinstance(value, PartialQuery):
            return self.attr != value.attr
        return ~(self == value)

    @_attr_delegate(Attr.__lt__)
    def __lt__(self, value: TNumberLike) -> Query:
        ...

    @_attr_delegate(Attr.__le__)
    def __le__(self, value: TNumberLike) -> Query:
        ...

    @_attr_delegate(Attr.__gt__)
    def __gt__(self, value: TNumberLike) -> Query:
        ...

    @_attr_delegate(Attr.__ge__)
    def __ge__(self, value: TNumberLike) -> Query:
        ...

    @_attr_delegate(Attr.__bool__)
    def __bool__(self) -> Query:
        ...

    @_attr_delegate(Attr.__contains__)
    def __contains__(self, value: Union[str, List[str], "Value[str]", "Value[List[str]]"]) -> Query:
        ...


T = TypeVar("T", bound="TValue")


@dataclass(frozen=True)
class Value(Generic[T]):
    """Represents a value in a query.

    In most cases values are unnecessary and can be replaced directly by the python
    value.

    Values can also be used if the Attr object appears on the right:

        Value("4HHB") == Attr("rcsb_entry_container_identifiers.entry_id")
    """

    value: T

    @overload  # type: ignore[override]
    def __eq__(self, attr: "Value") -> bool:
        ...

    @overload  # type: ignore[override]
    def __eq__(self, attr: Attr) -> Terminal:
        ...

    def __eq__(self, attr: Union["Value", Attr]) -> Union[bool, Terminal]:
        # type: ignore[override]
        if isinstance(attr, Value):
            return self.value == attr.value
        if not isinstance(attr, Attr):
            return NotImplemented
        return attr == self

    @overload  # type: ignore[override]
    def __ne__(self, attr: "Value") -> bool:
        ...

    @overload  # type: ignore[override]
    def __ne__(self, attr: Attr) -> Terminal:
        ...

    def __ne__(self, attr: Union["Value", Attr]) -> Union[bool, Terminal]:
        # type: ignore[override]
        if isinstance(attr, Value):
            return self.value != attr.value
        if not isinstance(attr, Attr):
            return NotImplemented
        return attr != self.value

    def __lt__(self, attr: Attr) -> Terminal:
        if not isinstance(attr, Attr):
            return NotImplemented
        if not (isinstance(self.value, int) or isinstance(self.value, float) or isinstance(self.value, date)):
            return NotImplemented
        return attr.greater(self.value)

    def __le__(self, attr: Attr) -> Terminal:
        if not isinstance(attr, Attr):
            return NotImplemented
        if not (isinstance(self.value, int) or isinstance(self.value, float) or isinstance(self.value, date)):
            return NotImplemented
        return attr.greater_or_equal(self.value)

    def __gt__(self, attr: Attr) -> Terminal:
        if not isinstance(attr, Attr):
            return NotImplemented
        if not (isinstance(self.value, int) or isinstance(self.value, float) or isinstance(self.value, date)):
            return NotImplemented
        return attr.less(self.value)

    def __ge__(self, attr: Attr) -> Terminal:
        if not isinstance(attr, Attr):
            return NotImplemented
        if not (isinstance(self.value, int) or isinstance(self.value, float) or isinstance(self.value, date)):
            return NotImplemented
        return attr.less_or_equal(self.value)


@dataclass(frozen=True)
class Range:
    """Primarily for use with "range" and "date_range" aggregations with the Facet class.
    include_upper and include_lower should not be used with Facet queries."""

    start: Union[str, float] = None
    end: Union[str, float] = None
    include_lower: Optional[bool] = None
    include_upper: Optional[bool] = None

    def to_dict(self) -> dict:
        d = {}
        if self.start is not None:
            d["from"] = self.start
        if self.end is not None:
            d["to"] = self.end
        if self.include_lower is not None:
            d["include_lower"] = self.include_lower
        if self.include_upper is not None:
            d["include_upper"] = self.include_upper
        return d


class Facet:
    """Facets can be used (in conjunction with the facet() function on a Query) in order to group and perform calculations and statistics on PDB data.
    Facets arrange search results into categories (buckets) based on the requested field values.
    """

    def __init__(
        self,
        name: str,
        aggregation_type: AggregationType,
        attribute: str,
        interval: Optional[Union[int, str]] = None,
        ranges: Optional[List[Range]] = None,
        min_interval_population: Optional[int] = None,
        max_num_intervals: Optional[int] = None,
        precision_threshold: Optional[int] = None,
        nested_facets: Optional[Union["Facet", "FilterFacet", List[Union["Facet", "FilterFacet"]]]] = None,
    ):
        """Initialize Facet object for use in a faceted query.

        Args:
            name (str): Specifies the name of the aggregation.
            aggregation_type (AggregationType): Specifies the type of the aggregation. Can be "terms", "histogram", "date_histogram", "range", "date_range", or "cardinality".
            attribute (str): Specifies the full attribute name to aggregate on.
            interval (Optional[Union[int, str]], optional): Size of the intervals into which a given set of values is divided. Required only for use with
            "histogram" and "date_histogram" aggregation types (defaults to None if not included).
            ranges (Optional[List[Range]], optional): A set of ranges, each representing a bucket. Note that this aggregation includes the 'from' value and
            excludes the 'to' value for each range. Should be a list of Range objects (leave the "include_lower" and "include_upper" fields empty). Required
            only for use with "range" and "date_range" aggregation types (defaults to None if not included).
            min_interval_population (Optional[int], optional): Minimum number of items (>= 0) in the bin required for the bin to be returned. Only for use with
            "terms", "histogram", and "date_histogram" facets (defaults to 1 for these aggregation types, otherwise defaults to None).
            max_num_intervals (Optional[int], optional): Maximum number of intervals (<= 65336) to return for a given facet. Only for use with "terms"
            aggregation type (defaults to 65336 for this aggregation type, otherwise defaults to None).
            precision_threshold (Optional[int], optional): Allows to trade memory for accuracy, and defines a unique count (<= 40000) below which counts are
            expected to be close to accurate. Only for use with "cardinality" aggregation type (defaults to 40000 for this aggregation type, otherwise defaults to None).
            nested_facets (Optional[Union[&quot;Facet&quot;, &quot;FilterFacet&quot;, List[Union[&quot;Facet&quot;, &quot;FilterFacet&quot;]]]], optional): Enables
            multi-dimensional aggregations. Should contain a List of Facets or FilterFacets. Can be used with any aggregation type. Defaults to None.
        """
        self.name = name
        self.aggregation_type = aggregation_type
        self.attribute = attribute
        self.interval = interval
        self.ranges = ranges
        self.min_interval_population = min_interval_population
        self.max_num_intervals = max_num_intervals
        self.precision_threshold = precision_threshold
        self.nested_facets = nested_facets if isinstance(nested_facets, list) or nested_facets is None else [nested_facets]

        if self.aggregation_type == "terms":
            if self.min_interval_population is None:
                self.min_interval_population = 1
            if self.max_num_intervals is None:
                self.max_num_intervals = 65536
        elif self.aggregation_type == "histogram":
            if self.min_interval_population is None:
                self.min_interval_population = 1
        elif self.aggregation_type == "date_histogram":
            if self.min_interval_population is None:
                self.min_interval_population = 1
        elif self.aggregation_type == "cardinality":
            if self.precision_threshold is None:
                self.precision_threshold = 40000

    def to_dict(self) -> dict:
        facet_dict = dict(name=self.name, aggregation_type=self.aggregation_type, attribute=self.attribute)
        if self.interval is not None:
            facet_dict["interval"] = self.interval
        if self.ranges is not None:
            facet_dict["ranges"] = [r.to_dict() for r in self.ranges]
        if self.min_interval_population is not None:
            facet_dict["min_interval_population"] = self.min_interval_population
        if self.max_num_intervals is not None:
            facet_dict["max_num_intervals"] = self.max_num_intervals
        if self.precision_threshold is not None:
            facet_dict["precision_threshold"] = self.precision_threshold
        if self.nested_facets is not None:
            facet_dict["facets"] = [f.to_dict() for f in self.nested_facets if f is not None]
        return facet_dict


class TerminalFilter:
    """
    Terminal filter class for use with FilterFacet queries
    """

    def __init__(
        self,
        attribute: str,
        operator: Literal["equals", "greater", "greater_or_equal", "less", "less_or_equal", "range", "exact_match", "in", "exists"],
        value: Optional[Union[str, int, float, bool, Range, List[str], List[int], List[float]]] = None,
        negation: bool = False,
        case_sensitive: bool = False,
    ):
        self.attribute = attribute
        self.operator = operator
        self.value = value
        self.negation = negation
        self.case_sensitive = case_sensitive

    def to_dict(self):
        tf_dict = dict(type="terminal", service="text", parameters=dict(attribute=self.attribute, operator=self.operator, negation=self.negation, case_sensitive=self.case_sensitive))
        if self.value is not None:
            tf_dict["parameters"]["value"] = self.value
        return tf_dict


class GroupFilter:
    """
    Group filter class for use with FilterFacet queries
    """

    def __init__(self, logical_operator: TAndOr, nodes: List[Union["TerminalFilter", "GroupFilter"]]):
        self.logical_operator = (logical_operator,)
        self.nodes = nodes

    def to_dict(self):
        return dict(type="group", logical_operator=self.logical_operator[0], nodes=[node.to_dict() for node in self.nodes])


class FilterFacet:
    """Facet queries using Filters"""

    def __init__(self, filters: Union[TerminalFilter, GroupFilter], facets: Union[Facet, "FilterFacet", List[Union[Facet, "FilterFacet"]]]):
        self.filter = filters
        self.facets = facets if isinstance(facets, list) else [facets]

    def to_dict(self):
        return dict(filter=self.filter.to_dict(), facets=[facet.to_dict() for facet in self.facets])


class Session(Iterable[str]):
    """A single query session.

    Handles paging the query and parsing results
    """

    url = RCSB_SEARCH_API_QUERY_URL
    query_id: str
    query: Query
    return_type: ReturnType
    start: int
    rows: int
    return_content_type: List[ReturnContentType]
    results_verbosity: VerbosityLevel
    facets: Optional[Union[Facet, FilterFacet, List[Union[Facet, FilterFacet]]]]

    def __init__(
        # parameter added below for computed model inclusion
        self,
        query: Query,
        return_type: ReturnType = "entry",
        rows: int = 10000,
        return_content_type: List[ReturnContentType] = ["experimental"],
        results_verbosity: VerbosityLevel = "compact",
        facets: Optional[Union[Facet, FilterFacet, List[Union[Facet, FilterFacet]]]] = None,
        # pylint: disable=dangerous-default-value
    ):
        self.query_id = Session.make_uuid()
        self.query = query.assign_ids()
        self.return_type = return_type
        self.start = 0
        self.rows = rows
        self.return_content_type = return_content_type
        self.results_verbosity = results_verbosity
        self.facets = facets

    @staticmethod
    def make_uuid() -> str:
        "Create a new UUID to identify a query"
        return uuid.uuid4().hex

    @staticmethod
    def _extract_identifiers(query_json: Optional[Dict]) -> List[str]:
        """Extract identifiers from a JSON response"""
        if query_json is None:
            return []

        # total_count = int(query_json["total_count"])
        identifiers = [result["identifier"] for result in query_json["result_set"]]
        # assert len(identifiers) == total_count, f"{len(identifiers)} != {total_count}"
        return identifiers

    def _make_params(self, start=0):
        "Generate GET parameters as a dict"
        query_dict = dict(
            query=self.query.to_dict(),
            return_type=self.return_type,
            request_info=dict(query_id=self.query_id, src="ui"),  # "TODO" src deprecated?
            # v1 -> v2: pager parameter is renamed to paginate and results_content_type parameter added (which has a list as its value)
            request_options=dict(paginate=dict(start=start, rows=self.rows), results_content_type=self.return_content_type, results_verbosity=self.results_verbosity),
        )
        if self.facets is not None:
            if type(self.facets) is list:
                query_dict["request_options"]["facets"] = [facet.to_dict() for facet in self.facets]
            else:
                query_dict["request_options"]["facets"] = [self.facets.to_dict()]
        return query_dict

    def _single_query(self, start=0) -> Optional[Dict]:
        "Fires a single query"
        params = self._make_params(start)
        logging.debug("Querying %s for results %s-%s", self.url, start, start + self.rows - 1)
        response = requests.get(self.url, {"json": json.dumps(params, separators=(",", ":"))}, timeout=None)
        response.raise_for_status()
        if response.status_code == requests.codes.ok:
            return response.json()
        elif response.status_code == requests.codes.no_content:
            return None
        else:
            raise requests.HTTPError(f"Unexpected status: {response.status_code}")

    def __iter__(self) -> Iterator[str]:
        "Generator for all results as a list of identifiers"
        start = 0
        req_count = 0
        response = self._single_query(start=start)
        if response is None:
            return  # be explicit for mypy
        result_set = response["result_set"] if response else []
        start += self.rows
        logging.debug("Got %s ids", len(result_set))

        if len(result_set) == 0:
            return
        yield from result_set

        total = response["total_count"]

        while start < total:
            assert len(result_set) == self.rows
            req_count += 1
            if req_count == REQUESTS_PER_SECOND:
                time.sleep(1.2)  # This prevents the user from bottlenecking the server with requests.
                req_count = 0
            response = self._single_query(start=start)
            result_set = response["result_set"] if response else []
            logging.debug("Got %s ids", len(result_set))
            start += self.rows
            yield from result_set

    def iquery(self, limit: Optional[int] = None) -> List[str]:
        """Evaluate the query and display an interactive progress bar.

        Requires tqdm.
        """
        from tqdm import trange  # type: ignore

        response = self._single_query(start=0)
        if response is None:
            return []
        total = response["total_count"]
        result_set = response["result_set"] if response else []
        if limit is not None and len(result_set) >= limit:
            return result_set[:limit]

        pages = math.ceil((total if limit is None else min(total, limit)) / self.rows)

        for page in trange(1, pages, initial=1, total=pages):
            response = self._single_query(page * self.rows)
            next_results = response["result_set"] if response else []
            result_set.extend(next_results)

        return result_set[:limit]

    def rcsb_query_editor_url(self) -> str:
        """URL to edit this query in the RCSB PDB query editor"""
        data = json.dumps(self._make_params(), separators=(",", ":"))
        return f"https://search.rcsb.org/query-editor.html?json={urllib.parse.quote(data)}"

    def rcsb_query_builder_url(self) -> str:
        """URL to view this query on the RCSB PDB website query builder"""
        params = self._make_params()
        params["request_options"]["paginate"]["rows"] = 25
        if "results_verbosity" in params["request_options"]:
            _ = params["request_options"].pop("results_verbosity")
        data = json.dumps(params, separators=(",", ":"))
        return f"https://www.rcsb.org/search?request={urllib.parse.quote(data)}"
