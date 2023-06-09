"""Interact with the [RCSB PDB Search API](https://search.rcsb.org/#search-api).
"""

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

if sys.version_info > (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal
# tqdm is optional

# Allowed return types for searches. http://search.rcsb.org/#return-type
ReturnType = Literal[
    "entry", "assembly", "polymer_entity", "non_polymer_entity", "polymer_instance"
]
TAndOr = Literal["and", "or"]
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

    def exec(self, return_type: ReturnType = "entry", rows: int = 10000) -> "Session":
        """Evaluate this query and return an iterator of all result IDs"""
        return Session(self, return_type, rows)

    def __call__(self, return_type: ReturnType = "entry", rows: int = 10000) -> "Session":
        """Evaluate this query and return an iterator of all result IDs"""
        return self.exec(return_type, rows)

    @overload
    def and_(self, other: "Query") -> "Query":
        ...

    @overload
    def and_(self, other: Union[str, "Attr"]) -> "PartialQuery":
        ...

    def and_(
        self, other: Union[str, "Query", "Attr"]
    ) -> Union["Query", "PartialQuery"]:
        """Extend this query with an additional attribute via an AND"""
        if isinstance(other, Query):
            return self & other
        elif isinstance(other, Attr):
            return PartialQuery(self, "and", other)
        elif isinstance(other, str):
            return PartialQuery(self, "and", Attr(other))
        else:
            raise TypeError(f"Expected Query or Attr, got {type(other)}")

    @overload
    def or_(self, other: "Query") -> "Query":
        ...

    @overload
    def or_(self, other: Union[str, "Attr"]) -> "PartialQuery":
        ...

    def or_(self, other: Union[str, "Query", "Attr"]) -> Union["Query", "PartialQuery"]:
        """Extend this query with an additional attribute via an OR"""
        if isinstance(other, Query):
            return self & other
        elif isinstance(other, Attr):
            return PartialQuery(self, "or", other)
        elif isinstance(other, str):
            return PartialQuery(self, "or", Attr(other))
        else:
            raise TypeError(f"Expected Query or Attr, got {type(other)}")


@dataclass(frozen=True)
class Terminal(Query):
    """A terminal query node.

    Terminals are simple predicates comparing some *attribute* of a structure to a
    value.

    Examples:
        >>> Terminal("exptl.method", "exact_match", "X-RAY DIFFRACTION")
        >>> Terminal("rcsb_id", "in", ["5T89", "1TIM"])
        >>> Terminal(value="tubulin")

    A full list of attributes is available in the
    `schema <http://search.rcsb.org/rcsbsearch/v2/metadata/schema>`_.
    Operators are documented `here <http://search.rcsb.org/#field-queries>`_.

    The :py:class:`Attr` class provides a more pythonic way of constructing Terminals.
    """

    attribute: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[TValue] = None
    service: str = "text"
    negation: Optional[bool] = False  # investigate whether this can be changed to None
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
            >>> Terminal("attr", "op", "val")
            >>> ~Terminal(value="val")

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

    def __init__(self, value: str):
        """Search for the string value anywhere in the text

        Args:
            value: free-text query
            negation: find structures without the pattern
        """
        super().__init__(service="full_text", value=value, negation=None)


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
            elif isinstance(other, Terminal):
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
    available in the `schema <http://search.rcsb.org/rcsbsearch/v2/metadata/schema>`_.

    * The `range` dictionary requires the following keys:
     * "from" -> int
     * "to" -> int
     * "include_lower" -> bool
     * "include_upper" -> bool
    """

    attribute: str

    def exact_match(self, value: Union[str, "Value[str]"]) -> Terminal:
        """Exact match with the value"""
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "exact_match", value)

    def contains_words(
        self, value: Union[str, "Value[str]", List[str], "Value[List[str]]"]
    ) -> Terminal:
        """Match any word within the string.

        Words are split at whitespace. All results which match any word are returned,
        with results matching more words sorted first.
        """
        if isinstance(value, Value):
            value = value.value
        if isinstance(value, list):
            value = " ".join(value)
        return Terminal(self.attribute, "contains_words", value)

    def contains_phrase(self, value: Union[str, "Value[str]"]) -> Terminal:
        """Match an exact phrase"""
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "contains_phrase", value)

    def greater(self, value: TNumberLike) -> Terminal:
        """Attribute > `value`"""
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "greater", value)

    def less(self, value: TNumberLike) -> Terminal:
        """Attribute < `value`"""
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "less", value)

    def greater_or_equal(self, value: TNumberLike) -> Terminal:
        """Attribute >= `value`"""
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "greater_or_equal", value)

    def less_or_equal(self, value: TNumberLike) -> Terminal:
        """Attribute <= `value`"""
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "less_or_equal", value)

    def equals(self, value: TNumberLike) -> Terminal:
        """Attribute == `value`"""
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "equals", value)

    def range(self, value: Dict[str, Any]) -> Terminal:
        """Attribute is within the specified half-open range

        Args:
            value: lower and upper bounds `[a, b)`
        """
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "range", value)

    def exists(self) -> Terminal:
        """Attribute is defined for the structure"""
        return Terminal(self.attribute, "exists")

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
    ) -> Terminal:
        """Attribute is contained in the list of values"""
        if isinstance(value, Value):
            value = value.value
        return Terminal(self.attribute, "in", value)

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
        elif (
            isinstance(value, date)
            or isinstance(value, float)
            or isinstance(value, int)
        ):
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

    def __contains__(
        self, value: Union[str, List[str], "Value[str]", "Value[List[str]]"]
    ) -> Terminal:
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
    def contains_words(
        self, value: Union[str, "Value[str]", List[str], "Value[List[str]]"]
    ) -> Query:
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
            return (
                self.attr == value.attr
                and self.query == value.query
                and self.operator == value.operator
            )

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
    def __contains__(
        self, value: Union[str, List[str], "Value[str]", "Value[List[str]]"]
    ) -> Query:
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
        if not (
            isinstance(self.value, int)
            or isinstance(self.value, float)
            or isinstance(self.value, date)
        ):
            return NotImplemented
        return attr.greater(self.value)

    def __le__(self, attr: Attr) -> Terminal:
        if not isinstance(attr, Attr):
            return NotImplemented
        if not (
            isinstance(self.value, int)
            or isinstance(self.value, float)
            or isinstance(self.value, date)
        ):
            return NotImplemented
        return attr.greater_or_equal(self.value)

    def __gt__(self, attr: Attr) -> Terminal:
        if not isinstance(attr, Attr):
            return NotImplemented
        if not (
            isinstance(self.value, int)
            or isinstance(self.value, float)
            or isinstance(self.value, date)
        ):
            return NotImplemented
        return attr.less(self.value)

    def __ge__(self, attr: Attr) -> Terminal:
        if not isinstance(attr, Attr):
            return NotImplemented
        if not (
            isinstance(self.value, int)
            or isinstance(self.value, float)
            or isinstance(self.value, date)
        ):
            return NotImplemented
        return attr.less_or_equal(self.value)


class Session(Iterable[str]):
    """A single query session.

    Handles paging the query and parsing results
    """

    url = "http://search.rcsb.org/rcsbsearch/v2/query"
    query_id: str
    query: Query
    return_type: ReturnType
    start: int
    rows: int

    def __init__(
        self, query: Query, return_type: ReturnType = "entry", rows: int = 10000
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
            request_info=dict(query_id=self.query_id, src="ui"),  # "TODO" src deprecated?
            request_options=dict(paginate=dict(start=start, rows=self.rows)),  # v1 -> v2: pager parameter is renamed to paginate
        )

    def _single_query(self, start=0) -> Optional[Dict]:
        "Fires a single query"
        params = self._make_params(start)
        logging.debug(
            "Querying %s for results %s-%s", self.url, start, start + self.rows - 1
        )
        response = requests.get(
            self.url, {"json": json.dumps(params, separators=(",", ":"))}, timeout=None
        )
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
        identifiers = self._extract_identifiers(response)
        start += self.rows
        logging.debug("Got %s ids", len(identifiers))

        if len(identifiers) == 0:
            return
        yield from identifiers

        total = response["total_count"]

        while start < total:
            assert len(identifiers) == self.rows
            req_count += 1
            if req_count == 10:
                time.sleep(1.2)  # This prevents the user from bottlenecking the server with requests.
                req_count = 0
            response = self._single_query(start=start)
            identifiers = self._extract_identifiers(response)
            logging.debug("Got %s ids", len(identifiers))
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

    def rcsb_query_editor_url(self) -> str:
        """URL to edit this query in the RCSB PDB query editor"""
        data = json.dumps(self._make_params(), separators=(",", ":"))
        return (
            f"http://search.rcsb.org/query-editor.html?json={urllib.parse.quote(data)}"
        )

    def rcsb_query_builder_url(self) -> str:
        """URL to view this query on the RCSB PDB website query builder"""
        data = json.dumps(self._make_params(), separators=(",", ":"))
        return f"http://www.rcsb.org/search?request={urllib.parse.quote(data)}"
