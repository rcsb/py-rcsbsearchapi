# rcsbsearch
Python interface for the RCSB search API.

Currently the 'text search' part of the API has been implemented.

This package requires python 3.7 or later.

## Usage

Searches are built up from a series of `Terminal` nodes. For example:

    from rcsbsearch import Terminal
    q1 = Terminal("rcsb_struct_symmetry.symbol", "exact_match", "C2")
    q2 = Terminal("rcsb_struct_symmetry.kind", "exact_match", "Global Symmetry")
    q3 = Terminal(value='"heat-shock transcription factor"')
    q4 = Terminal("rcsb_entry_info.polymer_entity_count_DNA", "greater_or_equal", 1)

These are combined using python's bitwise operators as if they were `set`s of results:

    q = q1 & q2 & q3 & q4  # AND of all queries

AND (`&`), OR (`|`), and terminal negation (`~`) are implemented directly by the API,
but the python package also implements set difference (`-`), symmetric difference (`^`),
and general negation by transforming the query.

Queries are executed by calling them as functions. They return an iterator of result
identifiers. Paging is handled transparently by the query.

    results = set(q())

By default PDB IDs are returned, but other result types are also supported:

    results = set(q("assembly"))

More control is available by executing the query using a Session object. For
instance, the `Session.iquery()` returns a list of all results. It uses the optional
`tqdm` package to track the progress of the query interactively.

    from rcsbsearch import Session
    session = Session(q)
    results = session.iquery()

Tests are run using tox and/or pytest.

    tox -e py37

or directly:

    pytest

## Code Style

Code conforms to the `black` and PEP8 style guides. Before checking in code, please run the linters:

    black .
    flake8
    mypy rcsbsearch

These are tested by the 'lint' tox environment:

    tox -e lint
