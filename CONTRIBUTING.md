# Contributing

## Testing

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


## Building docs

Docs are written in markdown and use sphinx to generate HTML files. The recommonmark
package is used for `.md` files, with sphinx-markdown-tables for table support.
Docstrings are parsed by `m2r`, which includes additional markdown extensions.

Building with tox:

    tox -e docs

Building manually:

    cd docs
    make html

## Making a release

### Setup

- Set up GPG key (for signing the tag)
- `pip install twine`
- Generate API token at TestPyPI and PyPI and add to .pypirc:

    [distutils]
        index-servers=
            pypi
            testpypi
    [pypi]
        username = __token__
        password = pypi-...
    [testpypi]
        repository: https://test.pypi.org/legacy/
        username = __token__
        password = pypi-...

- `chmod 600 ~/.pypirc`


### Release

1. Test

    tox

2. Build

    python setup.py sdist bdist_wheel

3. Tag

    git tag -s -a v0.1.0

4. Run checks

    twine check dist/*
    git verify-tag v0.1.0

4. Push to testing

    twine upload --repository testpypi -s --identity 780796DF dist/*

5. Push!

    git push
    git push --tags
    twine upload -s --identity 780796DF dist/*

6. Bump version number
