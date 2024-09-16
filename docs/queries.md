# Queries

## Constructing and Executing Queries
Two syntaxes are available for constructing queries: an "operator" syntax using Python's
comparators, and a "fluent" syntax where terms are chained together. Which to use is a
matter of preference, and both construct the same query object.

### Operator syntax
Searches are built up from a series of `Terminal` nodes, which compare structural
attributes to some search value. In the operator syntax, Python's comparator
operators are used to construct the comparison. The operators are overloaded to
return `Terminal` objects for the comparisons.

Here is an example from the [RCSB PDB Search API](http://search.rcsb.org/#search-example-1) page created using the operator syntax. 
This query finds symmetric dimers having a twofold rotation with the DNA-binding domain of a heat-shock transcription factor.
```python
from rcsbsearchapi.search import TextQuery
from rcsbsearchapi import rcsb_attributes as attrs

# Create terminals for each query
q1 = TextQuery("heat-shock transcription factor")
q2 = attrs.rcsb_struct_symmetry.symbol == "C2"
q3 = attrs.rcsb_struct_symmetry.kind == "Global Symmetry"
q4 = attrs.rcsb_entry_info.polymer_entity_count_DNA >= 1
```
Attributes are available from the rcsb_attributes object and can be tab-completed. 
They can additionally be constructed from strings using the `Attr(attribute)` constructor. 

For methods to search and find details on attributes within this package, go to the [attributes page](attributes.md)
For a full list of attributes, please refer to the [RCSB PDB schema](http://search.rcsb.org/rcsbsearch/v2/metadata/schema).

Individual `Terminal`s are combined into `Group`s using python's bitwise operators. This is
analogous to how bitwise operators act on python `set` objects. The operators are
lazy and won't perform the search until the query is executed.

```python
query = q1 & (q2 & q3 & q4)  # AND of all queries
```
AND (`&`), OR (`|`), and terminal negation (`~`) are implemented directly by the API,
but the python package also implements set difference (`-`), symmetric difference (`^`),
and general negation by transforming the query.

Queries are executed by calling them as functions. They return an iterator of result
identifiers.

```python
# Call the query to execute it
results = query()

for id in results:
    print(id)
```

By default, the query will return "entry" results (PDB IDs). It is also possible to
query other types of results (see [return-types](http://search.rcsb.org/#return-type)
for options):

```python
results = query(return_type="assembly")  # set return_type to "assembly"

for assembly_id in results:
    print(assembly_id)
```

### Fluent syntax
The operator syntax is great for simple queries, but requires parentheses or
temporary variables for complex nested queries. In these cases the fluent syntax may
be clearer. Queries are built up by appending operations sequentially.

Here is the same example using the fluent syntax

```python
from rcsbsearchapi.search import TextQuery, AttributeQuery, Attr

# Start with a Attr or TextQuery, then add terms
results = TextQuery("heat-shock transcription factor").and_(
    # Add attribute node as fully-formed AttributeQuery
    AttributeQuery(attribute="rcsb_struct_symmetry.symbol", operator="exact_match", value="C2") \

    # Add attribute node as Attr with chained operations
    # Setting type to "text" specifies that it's a Structure Attribute
    .and_(Attr(attribute="rcsb_struct_symmetry.kind", type="text")).exact_match("Global Symmetry") \

    # Add attribute node by name (converted to Attr) with chained operations
    .and_("rcsb_entry_info.polymer_entity_count_DNA").greater_or_equal(1) \

    # Execute the query and return assembly ids
    ).exec(return_type="assembly")

# Exec produces an iterator of IDs
for assembly_id in results:
    print(assembly_id)
```

### Structural Attribute Search and Chemical Attribute Search Combination
Grouping of Structural Attribute and Chemical Attribute queries is permitted. As Structure Attributes and Chemical Attributes are almost all unique, the package is able to determine the search service required. For attributes that are both Structure and Chemical Attributes (`rcsb_id`), specifying a search service is required.

More details on attributes that are available for text searches can be found on the [RCSB PDB Search API](https://search.rcsb.org/#search-attributes) page.

```python
from rcsbsearchapi.search import AttributeQuery

# Query for structures determined by electron microscopy
q1 = AttributeQuery(
    attribute="exptl.method",
    operator="exact_match",
    value="electron microscopy"
)

# Drugbank annotations contain phrase "tylenol"
q2 = AttributeQuery(
    attribute="drugbank_info.brand_names",
    operator="contains_phrase",
    value="tylenol"
)

# Combine queries with AND
query = q1 & q2

list(query())
```

```python
# "rcsb_id" is a Structure Attribute and Chemical Attribute
# So, search service must be specified

q1 = AttributeQuery(
    attribute="rcsb_id",
    operator="exact_match",
    value="4HHB",
    service="text"  # "text" specifies Structure Attribute search
)
list(q1())

q2 = AttributeQuery(
    attribute="rcsb_id",
    operator="exact_match",
    value="HEM",
    service="text_chem"  # "text_chem" specifies Chemical Attribute search
)
list(q2())
```

### Computed Structure Models
The [RCSB PDB Search API](https://search.rcsb.org/#results_content_type) page provides information on how to include Computed Structure Models (CSMs) into a search query. Here is a code example below.

This query returns IDs for experimental and computed structure models associated with "hemoglobin". Queries for *only* computed models or *only* experimental models can also be made (default).
```python
from rcsbsearchapi.search import TextQuery

q1 = TextQuery(value="hemoglobin")

# add parameter as a list with either "computational" or "experimental" or both
q2 = q1(return_content_type=["computational", "experimental"])

list(q2)
```

### Return Types and Attribute Search
A search query can return different result types when a return type is specified. 
Below are Structure Attribute query examples specifying return types Polymer Entities,
Non-polymer Entities, Polymer Instances, and Molecular Definitions. 


More information on return types can be found in the 
[RCSB PDB Search API](https://search.rcsb.org/#building-search-request) page.
```python
from rcsbsearchapi.search import AttributeQuery

# query for 4HHB deoxyhemoglobin
q1 = AttributeQuery(
    attribute="rcsb_entry_container_identifiers.entry_id",
    operator="in",
    value=["4HHB"]
)

# Polymer entities
for poly in q1(return_type="polymer_entity"):
    print(poly)
    
# Non-polymer entities
for nonPoly in q1(return_type="non_polymer_entity"):
    print(nonPoly)
    
# Polymer instances
for polyInst in q1(return_type="polymer_instance"):
    print(polyInst)
    
# Molecular definitions
for mol in q1(return_type="mol_definition"):
    print(mol)
```

## Counting Results
If only the number of results is desired, the count function can be used. This query returns the number of experimental models associated with "hemoglobin".
```python
from rcsbsearchapi.search import TextQuery

q1 = TextQuery(value="hemoglobin")

# As for `query()`, `return_type` and `return_content_type` can be parameters to `count()`
q1.count()
```

## Result Verbosity
Results can be returned alongside additional metadata, including result scores. To return this metadata, set the `results_verbosity` parameter to "verbose" (all metadata), "minimal" (scores only), or "compact" (default, no metadata). If set to "verbose" or "minimal", results will be returned as a list of dictionaries. 

For example, here we get all experimental models associated with "hemoglobin", along with their scores.

```python
from rcsbsearchapi.search import TextQuery

q1 = TextQuery(value="hemoglobin")
for idscore in list(q1(results_verbosity="minimal")):
    print(idscore)
```

## Sessions
The result of executing a query (either by calling it or using `exec()`) is a
`Session` object. It implements `__iter__`, so it is usually treated just as an
iterator of IDs.

Paging is handled transparently by the session, with additional API requests made
lazily as needed. The page size can be controlled with the `rows` parameter.
```python
first = next(iter(query(rows=1)))
```

### Progress Bar
The `Session.iquery()` method provides a progress bar indicating the number of API
requests being made. It requires the `tqdm` package be installed to track the
progress of the query interactively.
```python
results = query().iquery()
```
