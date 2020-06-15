# Queries

Two syntaxes are available for constructing queries: an "operator" API using python's
comparators, and a "builder" API where terms are chained together. Which to use is a
matter of preference, and both construct the same query object.

## Operator syntax

Searches are built up from a series of `Terminal` nodes, which compare structural
attributes to some search value. In the operator syntax, python's comparator
operators are used to construct the comparison. The operators are overloaded to
return `Terminal` objects for the comparisons.

    from rcsbsearch import Attr, TextQuery

    # Create terminals for each query
    q1 = TextQuery('"heat-shock transcription factor"')
    q2 = Attr("rcsb_struct_symmetry.symbol") == "C2"
    q3 = Attr("rcsb_struct_symmetry.kind") == "Global Symmetry"
    q4 = Attr("rcsb_entry_info.polymer_entity_count_DNA") >= 1

For a full list of attributes, please refer to the [RCSB
schema](http://search.rcsb.org/rcsbsearch/v1/metadata/schema).

`Terminal`s are combined into `Group`s using python's bitwise operators. This is
analogous to how bitwise operators act on python `set` objects. The operators are
lazy and won't perform the search until the query is executed.

    query = q1 & q2 & q3 & q4  # AND of all queries

AND (`&`), OR (`|`), and terminal negation (`~`) are implemented directly by the API,
but the python package also implements set difference (`-`), symmetric difference (`^`),
and general negation by transforming the query.

Queries are executed by calling them as functions. They return an iterator of result
identifiers.

    results = set(query())

By default, the query will return "entry" results (PDB IDs). It is also possible to
query other types of results (see [return-types](http://search.rcsb.org/#return-type)
for options):

    assemblies = set(query("assembly"))


## Builder syntax

The operator syntax is great for simple queries, but requires parentheses or
temporary variables for complex nested queries. In these cases the builder syntax may
be clearer. Queries are built up by appending operations sequentially.

    from rcsbsearch import Attr, TextQuery

    # Start with a Attr or TextQuery, then add terms
    results = TextQuery('"heat-shock transcription factor"') \
        .and_("rcsb_struct_symmetry.symbol").exact_match("C2") \
        .and_("rcsb_struct_symmetry.kind").exact_match("Global Symmetry") \
        .and_("rcsb_entry_info.polymer_entity_count_DNA").greater_or_equal(1) \
        .exec("assembly")

## Sessions

The result of executing a query (either by calling it or using `exec()`) is a
`Session` object. It implements `__iter__`, so it is usually treated just as an
iterator of IDs.

Paging is handled transparently by the session, with additional API requests made
lazily as needed. The page size can be controlled with the `rows` parameter.

    first = next(iter(query(rows=1)))

### Progress Bar

The `Session.iquery()` method provides a progress bar indicating the number of API
requests being made. It requires the `tqdm` package be installed to track the
progress of the query interactively.

    results = query().iquery()
