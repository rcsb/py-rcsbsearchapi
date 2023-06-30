# Quickstart

## Installation

Get it from pypi:

    pip install rcsbsearchapi

Or, download from [github](https://github.com/rcsb/py-rcsbsearchapi)

## Syntax

Here is a quick example of how the package is used. Two syntaxes are available for
constructing queries: an "operator" API using python's comparators, and a "fluent"
syntax where terms are chained together. Which to use is a matter of preference.

A runnable jupyter notebook with this example is available in [notebooks/quickstart.ipynb](notebooks/quickstart.ipynb), or can be run online using binder:
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/rcsb/py-rcsbsearchapi/master?labpath=notebooks%2Fquickstart.ipynb)

An additional example including a Covid-19 related example is in [notebooks/covid.ipynb](notebooks/covid.ipynb):
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/rcsb/py-rcsbsearchapi/master?labpath=notebooks%2Fcovid.ipynb)

### Operator example

Here is an example from the [RCSB Search
API](http://search.rcsb.org/#search-example-1) page, using the operator syntax. This
query finds symmetric dimers having a twofold rotation with the DNA-binding domain of
a heat-shock transcription factor.

    from rcsbsearchapi.search import TextQuery
    from rcsbsearchapi import rcsb_attributes as attrs

    # Create terminals for each query
    q1 = TextQuery('"heat-shock transcription factor"')
    q2 = attrs.rcsb_struct_symmetry.symbol == "C2"
    q3 = attrs.rcsb_struct_symmetry.kind == "Global Symmetry"
    q4 = attrs.rcsb_entry_info.polymer_entity_count_DNA >= 1

    # combined using bitwise operators (&, |, ~, etc)
    query = q1 & (q2 & q3 & q4)  # AND of all queries

    # Call the query to execute it
    for assemblyid in query("assembly"):
        print(assemblyid)

For a full list of attributes, please refer to the [RCSB
schema](http://search.rcsb.org/rcsbsearch/v2/metadata/schema).

### Fluent Example

Here is the same example using the fluent syntax

    from rcsbsearchapi.search import TextQuery
    from rcsbsearchapi.const import STRUCTURE_ATTRIBUTE_SEARCH_SERVICE

    # Start with a Attr or TextQuery, then add terms
    results = TextQuery("heat-shock transcription factor") \
    .and_(AttributeQuery("rcsb_struct_symmetry.symbol", "exact_match", "C2")
          .and_("rcsb_struct_symmetry.kind", STRUCTURE_ATTRIBUTE_SEARCH_SERVICE).exact_match("Global Symmetry")
          .and_("rcsb_entry_info.polymer_entity_count_DNA", STRUCTURE_ATTRIBUTE_SEARCH_SERVICE).greater_or_equal(1)
          ).exec("assembly")
    
    # Exec produces and iterator of IDs
    for assemblyid in results:
        print(assemblyid)

### Computed Structure Models

The [RCSB PDB Search API](https://search.rcsb.org/#results_content_type)
page provides information on how to include Computed Models into a search query. Here is a code example below.
This query returns ID's for experimental and computed models associated with "hemoglobin". 
Queries with only computed models or only experimental models can be made.
    
    from rcsbsearchapi.search import TextQuery
    
    q1 = TextQuery("hemoglobin")
    
    # add parameter as a list with either "computational" or "experimental" or both as list values
    q2 = q1(return_content_type=["computational", "experimental"])
    
    list(q2)

### Return Types and Attribute Search

A search query can return different result types when a return type is specified. 
Below are examples on specifying return types Polymer Entities,
Non-polymer Entities, Polymer Instances, and Molecular Definitions, using a Structure Attribute query. 
More information on return types can be found in the 
[RCSB PDB Search API](https://search.rcsb.org/#building-search-request) page.

    from rcsbsearchapi.search import AttributeQuery

    q1 = AttributeQuery("rcsb_entry_container_identifiers.entry_id", "in", ["4HHB"]) # query for 4HHB deoxyhemoglobin

    # Polymer entities
    for poly in q1("polymer_entity"): # include return type as a string parameter for query object
        print(poly)
    
    # Non-polymer entities
    for nonPoly in q1("non_polymer_entity"):
        print(nonPoly)
    
    # Polymer instances
    for polyInst in q1("polymer_instance"):
        print(polyInst)
    
    # Molecular definitions
    for mol in q1("mol_definition"):
        print(mol)

### Protein Sequence Search Example

Below is an example from the [RCSB PDB Search API](https://search.rcsb.org/#search-example-3) page, 
using the sequence search function.
This query finds macromolecular PDB entities that share 90% sequence identity with
GTPase HRas protein from *Gallus gallus* (*Chicken*).

    from rcsbsearchapi.search import SequenceQuery

    # Use SequenceQuery class and add parameters
    results = SequenceQuery("MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGET" +
                            "CLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQI" +
                            "KRVKDSDDVPMVLVGNKCDLPARTVETRQAQDLARSYGIPYIETSAKTRQ" +
                            "GVEDAFYTLVREIRQHKLRKLNPPDESGPGCMNCKCVIS", 1, 0.9)
    
    # Exec produces an iterator of IDs with return type - polymer entities
    for polyid in results("polymer_entity"):
        print(polyid)
