[![Build Status](https://travis-ci.org/sbliven/rcsbsearch.svg?branch=master)](https://travis-ci.org/sbliven/rcsbsearch)
[![Documentation Status](https://readthedocs.org/projects/rcsbsearch/badge/?version=latest)](https://rcsbsearch.readthedocs.io/en/latest/?badge=latest)

# rcsbsearch

Python interface for the RCSB search API.

Currently the 'text search' part of the API has been implemented.

This package requires python 3.7 or later.

## Example

Here is a quick example of how the package is used. Two syntaxes are available for
constructing queries: an "operator" API using python's comparators, and a "builder"
syntax where terms are chained together. Which to use is a matter of preference.

### Operator example

Here is an example from the [RCSB Search
API](http://search.rcsb.org/#search-example-1) page, using the operator syntax. This
query finds symmetric dimers having a twofold rotation with the DNA-binding domain of
a heat-shock transcription factor.

    from rcsbsearch import TextQuery
    from rcsbsearch import rcsb_attributes as attrs

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

### Builder Example

Here is the same example using the builder syntax

    from rcsbsearch import TextQuery

    # Start with a Attr or TextQuery, then add terms
    results = TextQuery('"heat-shock transcription factor"') \
        .and_("rcsb_struct_symmetry.symbol").exact_match("C2") \
        .and_("rcsb_struct_symmetry.kind").exact_match("Global Symmetry") \
        .and_("rcsb_entry_info.polymer_entity_count_DNA").greater_or_equal(1) \
        .exec("assembly")

    # Exec produces an iterator of IDs
    for assemblyid in results:
        print(assemblyid)

## Installation

Get it from pypi:

    pip install rcsbsearch

Or, download from [github](https://github.com/sbliven/rcsbsearch)

## Documentation

Detailed documentation is at [rcsbsearch.readthedocs.io](https://rcsbsearch.readthedocs.io/en/latest/)

## License

Code is licensed under the BSD 3-clause license. See [LICENSE](LICENSE) for details.

## Developers

For information about building and developing `rcsbsearch`, see
[CONTRIBUTING.md](CONTRIBUTING.md)
