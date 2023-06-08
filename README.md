[![PyPi Release](https://img.shields.io/pypi/v/rcsbsearchapi.svg)](https://pypi.org/project/rcsbsearchapi/)
[![Build Status](https://travis-ci.org/rcsb/rcsbsearchapi.svg?branch=master)](https://travis-ci.org/rcsb/rcsbsearchapi)
[![Documentation Status](https://readthedocs.org/projects/rcsbsearchapi/badge/?version=latest)](https://rcsbsearchapi.readthedocs.io/en/latest/?badge=latest)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/rcsb/rcsbsearchapi/master?filepath=notebooks%2Fcovid.ipynb)

# rcsbsearchapi

Python interface for the RCSB PDB Search API.

Currently the 'text search' part of the API has been implemented. See 'Supported
features' below.

This package requires python 3.7 or later.

## Example

Here is a quick example of how the package is used. Two syntaxes are available for
constructing queries: an "operator" API using python's comparators, and a "fluent"
syntax where terms are chained together. Which to use is a matter of preference.

A runnable jupyter notebook with this example is available in [notebooks/quickstart.ipynb](notebooks/quickstart.ipynb), or can be run online using binder:
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/rcsb/rcsbsearchapi/master?filepath=notebooks%2Fquickstart.ipynb)

An additional example including a Covid-19 related example is in [notebooks/covid.ipynb](notebooks/covid.ipynb):
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/rcsb/rcsbsearchapi/master?filepath=notebooks%2Fcovid.ipynb)

### Operator example

Here is an example from the [RCSB PDB Search
API](http://search.rcsb.org/#search-example-1) page, using the operator syntax. This
query finds symmetric dimers having a twofold rotation with the DNA-binding domain of
a heat-shock transcription factor.

    from rcsbsearchapi import TextQuery
    from rcsbsearchapi import rcsb_attributes as attrs

    # Create terminals for each query
    q1 = TextQuery('"heat-shock transcription factor"')
    q2 = attrs.rcsb_struct_symmetry.symbol == "C2"
    q3 = attrs.rcsb_struct_symmetry.kind == "Global Symmetry"
    q4 = attrs.rcsb_entry_info.polymer_entity_count_DNA >= 1

    # combined using bitwise operators (&, |, ~, etc)
    query = q1 & q2 & q3 & q4  # AND of all queries

    # Call the query to execute it
    for assemblyid in query("assembly"):
        print(assemblyid)

For a full list of attributes, please refer to the [RCSB PDB
schema](http://search.rcsb.org/rcsbsearch/v2/metadata/schema).

### Fluent Example

Here is the same example using the
[fluent](https://en.wikipedia.org/wiki/Fluent_interface) syntax.

    from rcsbsearchapi import TextQuery

    # Start with a Attr or TextQuery, then add terms
    results = TextQuery('"heat-shock transcription factor"') \
        .and_("rcsb_struct_symmetry.symbol").exact_match("C2") \
        .and_("rcsb_struct_symmetry.kind").exact_match("Global Symmetry") \
        .and_("rcsb_entry_info.polymer_entity_count_DNA").greater_or_equal(1) \
        .exec("assembly")

    # Exec produces an iterator of IDs
    for assemblyid in results:
        print(assemblyid)


## Supported Features

The following table lists the status of current and planned features.

- [x] Attribute Comparison operations
- [x] Query set operations
- [x] Attribute `contains`, `in_` (fluent only)
- [ ] Sequence search
- [ ] Sequence motif search
- [ ] Structural search
- [ ] Structural motif search
- [ ] Chemical search
- [ ] Rich results using the Data API

Contributions are welcome for unchecked items!

## Installation

Get it from pypi:

    pip install rcsbsearchapi

Or, download from [github](https://github.com/rcsb/py-rcsb_api_search)

## Documentation

Detailed documentation is at [rcsbsearchapi.readthedocs.io](https://rcsbsearchapi.readthedocs.io/en/latest/)

## License

Code is licensed under the BSD 3-clause license. See [LICENSE](LICENSE) for details.

## Citing rcsbsearchapi

Please cite the rcsbsearchapi package by URL:

> https://rcsbsearchapi.readthedocs.io

You should also cite the RCSB PDB service this package utilizes:

> Yana Rose, Jose M. Duarte, Robert Lowe, Joan Segura, Chunxiao Bi, Charmi
> Bhikadiya, Li Chen, Alexander S. Rose, Sebastian Bittrich, Stephen K. Burley,
> John D. Westbrook. RCSB Protein Data Bank: Architectural Advances Towards
> Integrated Searching and Efficient Access to Macromolecular Structure Data
> from the PDB Archive, Journal of Molecular Biology, 2020.
> DOI: [10.1016/j.jmb.2020.11.003](https://doi.org/10.1016/j.jmb.2020.11.003)

## Attributions

The source code for this project was originally written by [Spencer Bliven](https://github.com/sbliven) and forked
from https://github.com/sbliven/rcsbsearch. We would like to express our tremendous
gratitude for his generous efforts in designing such a comprehensive public utility
Python package for interacting with the RCSB PDB search API, [rcsbsearch](https://rcsbsearchapi.readthedocs.io).

## Developers

For information about building and developing `rcsbsearchapi`, see
[CONTRIBUTING.md](CONTRIBUTING.md)
