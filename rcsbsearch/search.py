"""Interact with the RCSB Search API.

https://search.rcsb.org/#search-api
"""

import uuid
import requests
import json
import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Union, Optional, List, Iterable, Tuple
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


class Query(ABC):
    """An RCSB query.

    Queries support set operators:

    - `q1 & q2`: Intersection (AND)
    - `q1 | q2`: Union (OR)
    - `~q1`: Negation (NOT)
    - `q1 - q2`: Difference (implemented as `q1 & ~q2`)
    - `q1 ^ q2`: Symmetric difference (XOR, implemented as `(q1 & ~q2) | (~q1 & q2)`)

    Note that only AND, OR, and negation of terminals are directly supported by
    the API, so other operations may be slower.

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
    """A terminal node
    """

    attribute: Optional[str] = None
    operator: Optional[str] = None
    value: Union[List, str, None] = None
    service: str = "text"
    negation: bool = False
    node_id: int = 0

    def __post_init__(self):
        # value is a required keyword argument
        assert self.value is not None

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

    Terminals can be constructed from Attributes using either a functional syntax, which
    mirrors the API operators, or with python operators.

    | Function         | Operator            |
    |------------------|---------------------|
    | exact_match      | attr == str         |
    | contains_words   | List[str] in attr   |
    | contains_phrase  | str in attr         |
    | greater          | attr > Date,number  |
    | less             | attr < Date,number  |
    | greater_or_equal | attr >= Date,number |
    | less_or_equal    | attr <= Date,number |
    | equals           | attr == Date,number |
    | range            | attr[start:end]     |
    | range_closed     |                     |
    | exists           | bool(attr)          |
    | in               | attr in value       |

    """

    attribute: str

    def exact_match(self, value: str):
        return Terminal(self.attribute, "exact_match", value)


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
