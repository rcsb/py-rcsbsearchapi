# Quickstart

## Installation

Get it from pypi:

    pip install rcsbsearch

Or, download from [github](https://github.com/rcsb/py-rcsb_api_search)

## Syntax

Here is a quick example of how the package is used. Two syntaxes are available for
constructing queries: an "operator" API using python's comparators, and a "fluent"
syntax where terms are chained together. Which to use is a matter of preference.

A runnable jupyter notebook with this example is available in [notebooks/quickstart.ipynb](notebooks/quickstart.ipynb), or can be run online using binder:
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/sbliven/rcsbsearch/master?filepath=notebooks%2Fquickstart.ipynb)

An additional example including a Covid-19 related example is in [notebooks/covid.ipynb](notebooks/covid.ipynb):
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/sbliven/rcsbsearch/master?filepath=notebooks%2Fcovid.ipynb)

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

For a full list of attributes, please refer to the [RCSB
schema](http://search.rcsb.org/rcsbsearch/v2/metadata/schema).

### Fluent Example

Here is the same example using the fluent syntax

    from rcsbsearch import Attr, TextQuery

    # Start with a Attr or TextQuery, then add terms
    results = TextQuery('"heat-shock transcription factor"') \
        .and_("rcsb_struct_symmetry.symbol").exact_match("C2") \
        .and_("rcsb_struct_symmetry.kind").exact_match("Global Symmetry") \
        .and_("rcsb_entry_info.polymer_entity_count_DNA").greater_or_equal(1) \
        .exec("assembly")

    # Exec produces an iterator of IDs
    for assemblyid in results:
        print(assemblyid)
