# rcsbsearch
Python interface for the RCSB search API.

## Testing

Tests are run using tox and/or pytest.

    tox -e py37

or directly:

    pytest

## Code Style

Code conforms to the `black` and PEP8 style guides. Before checking in code, please run the linters:

    black .
    flake8

These are tested by the 'lint' tox environment:

    tox -e lint
