"""Interact with the RCSB Search API.

https://search.rcsb.org/#search-api
"""

import uuid
import requests
import json
import logging
import math
from datetime import date
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Union, Optional, List, Iterable, Tuple, TypeVar, Generic
import sys

if sys.version_info > (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

# tqdm is optional

# Allowed return types for searches. http://search.rcsb.org/#return-type
ReturnType = Literal[
    "entry", "assembly", "polymer_entity", "non_polymer_entity", "polymer_instance"
]
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
]
# Types valid for numeric operators
TNumberLike = Union[int, float, date, "Value[int]", "Value[float]", "Value[date]"]


class Query(ABC):
    """Superclass for all types of queries.

    Queries support set operators:

    - `q1 & q2`: Intersection (AND)
    - `q1 | q2`: Union (OR)
    - `~q1`: Negation (NOT)
    - `q1 - q2`: Difference (implemented as `q1 & ~q2`)
    - `q1 ^ q2`: Symmetric difference (XOR, implemented as `(q1 & ~q2) | (~q1 & q2)`)

    Note that only AND, OR, and negation of terminals are directly supported by
    the API, so other operations may be slower.

    Queries can be executed by calling them as functions (`list(query())`)

    Queries are immutable.
    """

    @abstractmethod
    def to_dict(self) -> Dict:
        """Get dictionary representing this query"""
        ...

    def to_json(self) -> str:
        """Get JSON string of this query"""
        return json.dumps(self.to_dict, separators=(",", ":"))

    @abstractmethod
    def _assign_ids(self, node_id=0) -> Tuple["Query", int]:
        """Assign node_ids sequentially for all terminal nodes

        This is a helper for the assign_ids() method

        Returns a tuple with the modified query and the next available node_id
        """
        ...

    def assign_ids(self) -> "Query":
        """Assign node_ids sequentially for all terminal nodes

        Returns the modified query.
        """
        return self._assign_ids(0)[0]

    @abstractmethod
    def __invert__(self):
        """Negation: `~a`"""
        ...

    def __and__(self, other):
        """Intersection: `a & b`"""
        assert isinstance(other, Query)
        return Group("and", [self, other])

    def __or__(self, other):
        """Union: `a | b`"""
        assert isinstance(other, Query)
        return Group("or", [self, other])

    def __sub__(self, other):
        """Difference: `a - b`"""
        return self & ~other

    def __xor__(self, other):
        """Symmetric difference: `a ^ b`"""
        return (self & ~other) | (~self & other)

    def __call__(self, return_type: ReturnType = "entry", rows: int = 100):
        """Evaluate this query and return an iterator of all result IDs"""
        return Session(self, return_type, rows)


@dataclass(frozen=True)
class Terminal(Query):
    """A terminal query node.

    Terminals are simple predicates comparing some *attribute* of a structure to a
    value.

    Examples:

        Terminal("exptl.method", "exact_match", "X-RAY DIFFRACTION")
        Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["5T89", "1TIM"])
        Terminal(value="tubulin")

    A full list of attributes is available in the
    [schema](http://search.rcsb.org/rcsbsearch/v1/metadata/schema).
    Operators are documented [here](http://search.rcsb.org/#field-queries).

    The `Attr` class provides a more pythonic way of constructing Terminals.
    """

    attribute: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[TValue] = None
    service: str = "text"
    negation: bool = False
    node_id: int = 0

    def to_dict(self):
        params = dict()
        if self.attribute is not None:
            params["attribute"] = self.attribute
        if self.operator is not None:
            params["operator"] = self.operator
        if self.value is not None:
            params["value"] = self.value
        if self.negation is not None:
            params["negation"] = self.negation

        return dict(
            type="terminal",
            service=self.service,
            parameters=params,
            node_id=self.node_id,
        )

    def __invert__(self):
        return Terminal(
            self.attribute,
            self.operator,
            self.value,
            self.service,
            not self.negation,
            self.node_id,
        )

    def _assign_ids(self, node_id=0) -> Tuple[Query, int]:
        if self.node_id == node_id:
            return (self, node_id + 1)
        else:
            return (
                Terminal(
                    self.attribute,
                    self.operator,
                    self.value,
                    self.service,
                    self.negation,
                    node_id,
                ),
                node_id + 1,
            )

    def __str__(self):
        """Return a simplified string representation

        Examples:

            Terminal("attr", "op", "val")
            ~Terminal(value="val")

        """
        negation = "~" if self.negation else ""
        if self.attribute is None and self.operator is None:
            # value-only
            return f"{negation}Terminal(value={self.value!r})"
        else:
            return (
                f"{negation}Terminal({self.attribute!r}, {self.operator!r}, "
                f"{self.value!r})"
            )


class TextQuery(Terminal):
    """Special case of a Terminal for free-text queries"""

    def __init__(self, value: str, negation: bool = False):
        """Search for the string value anywhere in the text"""
        super().__init__(value=value, negation=negation)


@dataclass(frozen=True)
class Group(Query):
    """AND and OR combinations of queries"""

    operator: Literal["and", "or"]
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

    def __and__(self, other):
        # Combine nodes if possible
        if self.operator == "and":
            if isinstance(other, Terminal):
                return Group("and", self.nodes + [other])
            elif isinstance(other, Group) and other.operator == "and":
                return Group("and", self.nodes + other.nodes)

        return super(self).__and__(other)

    def __or__(self, other):
        # Combine nodes if possible
        if self.operator == "or":
            if isinstance(other, Terminal):
                return Group("or", self.nodes + [other])
            elif isinstance(other, Group) and other.operator == "or":
                return Group("or", self.nodes + other.nodes)

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
        if self.operator == "and":
            return f"({' & '.join((str(n) for n in self.nodes))})"
        elif self.operator == "or":
            return f"({' | '.join((str(n) for n in self.nodes))})"
        else:
            raise ValueError("Illegal Operator")


@dataclass(frozen=True)
class Attr:
    """A search attribute, e.g. "rcsb_entry_container_identifiers.entry_id"

    Terminals can be constructed from Attr objects using either a functional syntax,
    which mirrors the API operators, or with python operators.

    | Function         | Operator            |
    |------------------|---------------------|
    | exact_match      | attr == str         |
    | contains_words   | List[str] in attr   |
    | contains_phrase  | str in attr         |
    | greater          | attr > date,number  |
    | less             | attr < date,number  |
    | greater_or_equal | attr >= date,number |
    | less_or_equal    | attr <= date,number |
    | equals           | attr == date,number |
    | range            | attr[start:end]     |
    | range_closed     |                     |
    | exists           | bool(attr)          |
    | in_              | attr in Value(val)  |

    Rather than their normal bool return values, operators return Terminals.
    """

    attribute: str

    def exact_match(self, value: Union[str, "Value[str]"]):
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "exact_match", value)

    def contains_words(self, value: Union[List[str], "Value[List[str]]"]):
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "contains_words", value)

    def contains_phrase(self, value: Union[str, "Value[str]"]):
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "contains_phrase", value)

    def greater(self, value: TNumberLike):
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "greater", value)

    def less(self, value: TNumberLike):
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "less", value)

    def greater_or_equal(self, value: TNumberLike):
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "greater_or_equal", value)

    def less_or_equal(self, value: TNumberLike):
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "less_or_equal", value)

    def equals(self, value: TNumberLike):
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "equals", value)

    def range(self, value: Union[List[int], Tuple[int, int]]):
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "range", value)

    def range_closed(
        self,
        value: Union[
            List[int], Tuple[int, int], "Value[List[int]]", "Value[Tuple[int, int]]"
        ],
    ):
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "range_closed", value)

    def exists(self):
        return Terminal(self.attribute, "exists")

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
    ):
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "in", value)

    def __eq__(self, value):
        if isinstance(value, Value):
            value = value.value
        if isinstance(value, str):
            return self.exact_match(value)
        elif (
            isinstance(value, date)
            or isinstance(value, float)
            or isinstance(value, int)
        ):
            return self.equals(value)
        else:
            return NotImplemented

    def __lt__(self, value: TNumberLike):
        if isinstance(value, Value):
            value = value.value
        return self.less(value)

    def __le__(self, value: TNumberLike):
        if isinstance(value, Value):
            value = value.value
        return self.less_or_equal(value)

    def __ne__(self, value):
        if isinstance(value, Value):
            value = value.value
        return ~(self == value)

    def __gt__(self, value: TNumberLike):
        if isinstance(value, Value):
            value = value.value
        return self.greater(value)

    def __ge__(self, value: TNumberLike):
        if isinstance(value, Value):
            value = value.value
        return self.greater_or_equal(value)

    def __bool__(self):
        return self.exists()

    def __contains__(self, value):
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
            return self.contains_phrase(value)


T = TypeVar("T", bound="TValue")


@dataclass(frozen=True)
class Value(Generic[T]):
    """Represents a value in a query.

    In most cases values are unnecessary and can be replaced directly by the python
    value. The exception is the 'in' operator, which must be called on a Value object
    due to the way python handles operator overloading:

        Attr("rcsb_struct_symmetry.type") in Value(["C4", "D2"])

    Values can also be used if the Attr object appears on the right:

        Value("4HHB") == Attr("rcsb_entry_container_identifiers.entry_id")
    """

    value: T

    def __contains__(self, attr: Attr):
        "Implements `attr in Value(...)`"
        if not isinstance(attr, Attr):
            return NotImplemented
        # Valid TSimpleNumberLike constraints
        if (
            isinstance(self.value, int)
            or isinstance(self.value, float)
            or isinstance(self.value, date)
        ):
            return attr.in_(self.value)
        return NotImplemented

    def __eq__(self, attr):
        if not isinstance(attr, Attr):
            return NotImplemented
        return attr == self

    def __lt__(self, attr: Attr):
        if not isinstance(attr, Attr):
            return NotImplemented
        if not (
            isinstance(self.value, int)
            or isinstance(self.value, float)
            or isinstance(self.value, date)
        ):
            return NotImplemented
        return attr.greater(self.value)

    def __le__(self, attr: Attr):
        if not isinstance(attr, Attr):
            return NotImplemented
        if not (
            isinstance(self.value, int)
            or isinstance(self.value, float)
            or isinstance(self.value, date)
        ):
            return NotImplemented
        return attr.greater_or_equal(self.value)

    def __ne__(self, attr):
        if not isinstance(attr, Attr):
            return NotImplemented
        return attr != self.value

    def __gt__(self, attr: Attr):
        if not isinstance(attr, Attr):
            return NotImplemented
        if not (
            isinstance(self.value, int)
            or isinstance(self.value, float)
            or isinstance(self.value, date)
        ):
            return NotImplemented
        return attr.less(self.value)

    def __ge__(self, attr: Attr):
        if not isinstance(attr, Attr):
            return NotImplemented
        if not (
            isinstance(self.value, int)
            or isinstance(self.value, float)
            or isinstance(self.value, date)
        ):
            return NotImplemented
        return attr.less_or_equal(self.value)


class Session(object):
    """A single query session.

    Handles paging the query and parsing results
    """

    url = "http://search.rcsb.org/rcsbsearch/v1/query"
    query_id: str
    query: Query
    return_type: ReturnType
    start: int
    rows: int

    def __init__(
        self, query: Query, return_type: ReturnType = "entry", rows: int = 100
    ):
        self.query_id = Session.make_uuid()
        self.query = query.assign_ids()
        self.return_type = return_type
        self.start = 0
        self.rows = rows

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
        return dict(
            query=self.query.to_dict(),
            return_type=self.return_type,
            request_info=dict(query_id=self.query_id, src="ui"),  # TODO src deprecated?
            request_options=dict(pager=dict(start=start, rows=self.rows)),
        )

    def _single_query(self, start=0) -> Optional[Dict]:
        "Fires a single query"
        params = self._make_params(start)
        logging.debug(
            f"Querying {self.url} for results {start}-{start + self.rows - 1}"
        )
        response = requests.get(
            self.url, {"json": json.dumps(params, separators=(",", ":"))}
        )
        response.raise_for_status()
        if response.status_code == requests.codes.OK:
            return response.json()
        elif response.status_code == requests.codes.NO_CONTENT:
            return None
        else:
            raise Exception(f"Unexpected status: {response.status_code}")

    def __iter__(self) -> Iterable[str]:
        "Generator for all results as a list of identifiers"
        start = 0
        response = self._single_query(start=start)
        if response is None:
            return  # be explicit for mypy
        identifiers = self._extract_identifiers(response)
        start += self.rows
        logging.debug(f"Got {len(identifiers)} ids")

        if len(identifiers) == 0:
            return
        yield from identifiers

        total = response["total_count"]

        while start < total:
            assert len(identifiers) == self.rows
            response = self._single_query(start=start)
            identifiers = self._extract_identifiers(response)
            logging.debug(f"Got {len(identifiers)} ids")
            start += self.rows
            yield from identifiers

    def iquery(self, limit: Optional[int] = None) -> List[str]:
        """Evaluate the query and display an interactive progress bar.

        Requires tqdm.
        """
        from tqdm import trange  # type: ignore

        response = self._single_query(start=0)
        if response is None:
            return []
        total = response["total_count"]
        identifiers = self._extract_identifiers(response)
        if limit is not None and len(identifiers) >= limit:
            return identifiers[:limit]

        pages = math.ceil((total if limit is None else min(total, limit)) / self.rows)

        for page in trange(1, pages, initial=1, total=pages):
            response = self._single_query(page * self.rows)
            ids = self._extract_identifiers(response)
            identifiers.extend(ids)

        return identifiers[:limit]


# %%
