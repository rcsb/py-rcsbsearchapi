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
from typing import Dict, Union, Optional, List, Iterable

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

# tqdm is optional


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
    def _assign_ids(self, node_id=0) -> ("Query", int):
        """Assign node_ids sequentially for all terminal nodes

        This is a helper for the assign_ids() method

        Returns a tuple with the modified query and the next available node_id
        """
        ...

    def assign_ids(self) -> ("Query", int):
        """Assign node_ids sequentially for all terminal nodes

        Returns the modified query.
        """
        return self._assign_ids(0)[0]

    @abstractmethod
    def __inv__(self):
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


@dataclass(frozen=True)
class Terminal(Query):
    """A terminal node
    """

    attribute: str
    operator: str
    value: Union[List, str]
    service: str = "text"
    negation: bool = False
    node_id: int = 0

    def to_dict(self):
        return dict(
            type="terminal",
            service=self.service,
            parameters=dict(
                attribute=self.attribute,
                operator=self.operator,
                value=self.value,
                negation=self.negation,
            ),
            node_id=self.node_id,
        )

    def __inv__(self):
        return Terminal(
            self.attribute,
            self.operator,
            self.value,
            self.service,
            not self.negation,
            self.node_id,
        )

    def _assign_ids(self, node_id=0) -> (Query, int):
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

    def __inv__(self):
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

        return super(self).__or__(other)

    def _assign_ids(self, node_id=0) -> (Query, int):
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
            return self


class Session(object):
    """A single query session.

    Handles paging the query and parsing results
    """

    url = "http://search.rcsb.org/rcsbsearch/v1/query"

    def __init__(self, query: Query, return_type="entry", rows=100):
        self.query_id = Session.make_uuid()
        self.query = query.assign_ids()
        self.return_type = return_type
        self.start = 0
        self.rows = rows

    @staticmethod
    def make_uuid():
        "Create a new UUID to identify a query"
        return uuid.uuid4().hex

    @staticmethod
    def _extract_identifiers(query_json):
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

    def __iter__(self):
        "Generator for all results as a list of identifiers"
        start = 0
        response = self._single_query(start=start)
        identifiers = self._extract_identifiers(response)
        start += self.rows
        print(f"Got {len(identifiers)} ids")

        if len(identifiers) == 0:
            return

        yield from identifiers

        total = response["total_count"]

        while start < total:
            assert len(identifiers) == self.rows
            response = self._single_query(start=start)
            identifiers = self._extract_identifiers(response)
            print(f"Got {len(identifiers)} ids")
            start += self.rows
            yield from identifiers

    def iquery(self, limit: Optional[int] = None) -> List[str]:
        """Evaluate the query and display an interactive progress bar.

        Requires tqdm.
        """
        from tqdm import trange

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
