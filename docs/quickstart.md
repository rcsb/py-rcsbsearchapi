# Quickstart

## Installation

Get it from PyPI:

    pip install rcsbsearchapi

Or, download from [GitHub](https://github.com/rcsb/py-rcsbsearchapi)

## Getting Started

To perform a general search for structures associated with the phrase "Hemoglobin", you can create a TextQuery. This does a "full-text" search, which is a general search on text associated with PDB structures or molecular definitions. Learn more about available search services on the [RCSB PDB Search API docs](https://search.rcsb.org/#search-services).
```python
from rcsbsearchapi import TextQuery

# Search for structures associated with the phrase "Hemoglobin"
query = TextQuery(value="Hemoglobin")

# Execute the query by running it as a function
results = query()

# Results are returned as an iterator of result identifiers.
for id in results:
    print(id)
```

Besides general text searches, you can also search for specific structure or chemical attributes. 

Using different operators such as `contains_phrase` or `exact_match`, attributes can be compared to a value.
You can also check whether an attribute exists for a given structure by using the `exists` operator. 

Refer to the [Search Attributes](https://search.rcsb.org/structure-search-attributes.html) and [Chemical Attributes](https://search.rcsb.org/chemical-search-attributes.html) documentation for a full list of attributes and applicable operators.

To search an attribute, you can make an AttributeQuery.
```python
from rcsbsearchapi import AttributeQuery

# Construct the query
query = AttributeQuery(
    attribute="rcsb_entity_source_organism.scientific_name",
    operator="exact_match",  # other operators include "contains phrase" and "exists"
    value="Homo sapiens"
)
results = list(query())  # construct a list from query results
print(results)
```

When using certain operators such as `exact_match`, `greater`, or `less`, you can also use `rcsb_attributes` (imported below as `attrs`).

Using this syntax, attribute names can be tab-completed. 

```python
from rcsbsearchapi import rcsb_attributes as attrs

# Search for structures from humans
query = attrs.rcsb_entity_source_organism.scientific_name == "Homo sapiens"
results = list(query())  # construct a list from query results
print(results)
```

You can combine multiple queries using Python bitwise operators. 

|Operator|Description             |
|--------|------------------------|
|&       |AND                     |
|\|      |OR                      |
|~       |NOT                     |
|-       |set difference          |
|^       |symmetric difference/XOR|

```python
from rcsbsearchapi import rcsb_attributes as attrs

# Query for human epidermal growth factor receptor (EGFR) structures with investigational or experimental drugs
# EGFR is involved in cell division and often overexpressed or mutated in some cancers
q1 = attrs.rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession == "P00533"
q2 = attrs.rcsb_entity_source_organism.scientific_name == "Homo sapiens"
q3 = attrs.drugbank_info.drug_groups == "investigational"
q4 = attrs.drugbank_info.drug_groups == "experimental"

# Structures matching UniProt id P00533 AND from humans AND (investigational or experimental drug group)
query = q1 & q2 & (q3 | q4)

# Execute query and print first 10 ids
results = list(query())
print(results[:10])
```

These examples are in `operator syntax`. You can also make queries in `fluent syntax`. Learn more about both syntaxes and implementation details in [Queries](queries.md#constructing-and-executing-queries).

## Jupyter Notebooks
A runnable jupyter notebook with this example is available in [notebooks/quickstart.ipynb](notebooks/quickstart.ipynb), or can be run online using Google Colab:
<a href="https://colab.research.google.com/github/rcsb/py-rcsbsearchapi/blob/master/notebooks/quickstart.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

An additional example including a Covid-19 related example is in [notebooks/covid.ipynb](notebooks/covid.ipynb):
<a href="https://colab.research.google.com/github//rcsb/py-rcsbsearchapi/blob/master/notebooks/covid.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>