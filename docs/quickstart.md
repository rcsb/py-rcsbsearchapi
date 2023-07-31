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
```python
from rcsbsearchapi.search import TextQuery
from rcsbsearchapi import rcsb_attributes as attrs

# Create terminals for each query
q1 = TextQuery("heat-shock transcription factor")
q2 = attrs.rcsb_struct_symmetry.symbol == "C2"
q3 = attrs.rcsb_struct_symmetry.kind == "Global Symmetry"
q4 = attrs.rcsb_entry_info.polymer_entity_count_DNA >= 1

# combined using bitwise operators (&, |, ~, etc)
query = q1 & (q2 & q3 & q4)

# Call the query to execute it
for assemblyid in query("assembly"):
    print(assemblyid)
```
For a full list of attributes, please refer to the [RCSB
schema](http://search.rcsb.org/rcsbsearch/v2/metadata/schema).

### Fluent Example

Here is the same example using the fluent syntax
```python
from rcsbsearchapi.search import TextQuery, AttributeQuery, Attr

# Start with a Attr or TextQuery, then add terms
results = TextQuery("heat-shock transcription factor").and_(
    # Add attribute node as fully-formed AttributeQuery
    AttributeQuery("rcsb_struct_symmetry.symbol", "exact_match", "C2") \
    # Add attribute node as Attr with chained operations
    .and_(Attr("rcsb_struct_symmetry.kind")).exact_match("Global Symmetry") \
    # Add attribute node by name (converted to Attr) with chained operations
    .and_("rcsb_entry_info.polymer_entity_count_DNA").greater_or_equal(1)
    ).exec("assembly")

# Exec produces an iterator of IDs
for assemblyid in results:
    print(assemblyid)
```
### Structural Attribute Search and Chemical Attribute Search Combination

Grouping of a Structural Attribute query and Chemical Attribute query is permitted as long as grouping is done correctly and search services are specified accordingly. Not the example below. More details on attributes that are available for text searches can be found on the [RCSB PDB Search API](https://search.rcsb.org/#search-attributes) page.
```python
from rcsbsearchapi.const import CHEMICAL_ATTRIBUTE_SEARCH_SERVICE, STRUCTURE_ATTRIBUTE_SEARCH_SERVICE
from rcsbsearchapi.search import AttributeQuery

# By default, service is set to "text" for structural attribute search
q1 = AttributeQuery("exptl.method", "exact_match", "electron microscopy",
                    STRUCTURE_ATTRIBUTE_SEARCH_SERVICE # this constant specifies "text" service
                    )

# Need to specify chemical attribute search service - "text_chem"
q2 = AttributeQuery("drugbank_info.brand_names", "contains_phrase", "tylenol",
                    CHEMICAL_ATTRIBUTE_SEARCH_SERVICE # this constant specifies "text_chem" service
                    )

query = q1 & q2 # combining queries

list(query())
```
### Computed Structure Models

The [RCSB PDB Search API](https://search.rcsb.org/#results_content_type)
page provides information on how to include Computed Models into a search query. Here is a code example below.
This query returns ID's for experimental and computed models associated with "hemoglobin". 
Queries with only computed models or only experimental models can be made.
```python
from rcsbsearchapi.search import TextQuery
    
q1 = TextQuery("hemoglobin")

# add parameter as a list with either "computational" or "experimental" or both as list values
q2 = q1(return_content_type=["computational", "experimental"])

list(q2)
```
### Return Types and Attribute Search

A search query can return different result types when a return type is specified. 
Below are examples on specifying return types Polymer Entities,
Non-polymer Entities, Polymer Instances, and Molecular Definitions, using a Structure Attribute query. 
More information on return types can be found in the 
[RCSB PDB Search API](https://search.rcsb.org/#building-search-request) page.
```python
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
```
### Protein Sequence Search Example

Below is an example from the [RCSB PDB Search API](https://search.rcsb.org/#search-example-3) page, 
using the sequence search function.
This query finds macromolecular PDB entities that share 90% sequence identity with
GTPase HRas protein from *Gallus gallus* (*Chicken*).
```python
from rcsbsearchapi.search import SequenceQuery

# Use SequenceQuery class and add parameters
results = SequenceQuery("MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGET" +
                        "CLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQI" +
                        "KRVKDSDDVPMVLVGNKCDLPARTVETRQAQDLARSYGIPYIETSAKTRQ" +
                        "GVEDAFYTLVREIRQHKLRKLNPPDESGPGCMNCKCVIS", 1, 0.9)
    
# results("polymer_entity") produces an iterator of IDs with return type - polymer entities
for polyid in results("polymer_entity"):
    print(polyid)
```
### Sequence Motif Search Example

Below is an example from the [RCSB PDB Search API](https://search.rcsb.org/#search-example-6) page,
using the sequence motif search function. 
This query retrives occurences of the His2/Cys2 Zinc Finger DNA-binding domain as
represented by its PROSITE signature. 
```python
from rcsbsearchapi.search import SeqMotifQuery

# Use SeqMotifQuery class and add parameters
results = SeqMotifQuery("C-x(2,4)-C-x(3)-[LIVMFYWC]-x(8)-H-x(3,5)-H.",
                        pattern_type="prosite",
                        sequence_type="protein")

# results("polymer_entity") produces an iterator of IDs with return type - polymer entities
for polyid in results("polymer_entity"):
    print(polyid)
```

You can also use a regular expression (RegEx) to make a sequence motif search.
As an example, here is a query for the zinc finger motif that binds Zn in a DNA-binding domain:
```python
from rcsbsearchapi.search import SeqMotifQuery

results = SeqMotifQuery("C.{2,4}C.{12}H.{3,5}H", pattern_type="regex", sequence_type="protein")

for polyid in results("polymer_entity"):
    print(polyid)
```

You can use a standard amino acid sequence to make a sequence motif search. 
X can be used to allow any amino acid in that position. 
As an example, here is a query for SH3 domains:
```python
from rcsbsearchapi.search import SeqMotifQuery

# By default, the pattern_type argument is "simple" and the sequence_type argument is "protein".
results = SeqMotifQuery("XPPXP")  # X is used as a "variable residue" and can be any amino acid. 

for polyid in results("polymer_entity"):
    print(polyid)
```

All 3 of these pattern types can be used to search for DNA and RNA sequences as well.
Demonstrated are 2 queries, one DNA and one RNA, using the simple pattern type:
```python
from rcsbsearchapi.search import SeqMotifQuery

# DNA query: this is a query for a T-Box.
dna = SeqMotifQuery("TCACACCT", sequence_type="dna")

print("DNA results:")
for polyid in dna("polymer_entity"):
    print(polyid)

# RNA query: 6C RNA motif
rna = SeqMotifQuery("CCCCCC", sequence_type="rna")
print("RNA results:")
for polyid in rna("polymer_entity"):
    print(polyid)
```
### Structure Similarity Query Example

The PDB archive can be queried using the 3D shape of a protein structure. To perform this query, 3D protein structure data must be provided as an input or parameter, A chain ID or assembly ID must be specified, whether the input structure data should be compared to Assemblies or Polymer Entity Instance (Chains) is required, and defining the search type as either strict or relaxed is required. More information on how Structure Similarity Queries work can be found on the [RCSB PDB Structure Similarity Search](https://www.rcsb.org/docs/search-and-browse/advanced-search/structure-similarity-search) page.
```python
from rcsbsearchapi.search import StructSimilarityQuery

# Basic query: querying using entry ID and default values assembly ID "1", operator "strict", and target search space "Assemblies"
q1 = StructSimilarityQuery(value="4HHB")

# Same example but with parameters explicitly specified
q1 = StructSimilarityQuery(structure_search_type="entry_id",
                           value="4HHB",
                           input_structure_type="assembly_id",
                           input_option="1",
                           operator="strict_shape_match",
                           target_search_space="assembly"
                           )
for id in q1("assembly"):
    print(id)
```
Below is a more complex example that utilizes chain ID, relaxed search operator, and polymer entity instance or target search space. Specifying whether the input structure
type is chain id or assembly id is very important. For example, specifying chain ID as the input structure type but inputting an assembly ID can lead to
an error.
```python
from rcsbsearchapi.search import StructSimilarityQuery

# More complex query with entry ID value "4HHB", chain ID "B", operator "relaxed", and target search space "Chains"
q2 = StructSimilarityQuery(structure_search_type="entry_id",
                                   value="4HHB",
                                   input_structure_type="chain_id",
                                   input_option="B",
                                   operator="relaxed_shape_match",
                                   target_search_space="polymer_entity_instance")
list(q2())
```
Structure similarity queries also allow users to upload a file from their local computer or input a file url from the website to query the PDB archive for similar proteins. The file represents a target protein structure in the file formats "cif", "bcif", "pdb", "cif.gz", or "pdb.gz". If a user wants to use a file url for queries, the user must specify the structure search type, the value (being the url), and the file format of the file. This is also the same case for file upload, except the value is the absolute path leading to the file that is in the local machine. An example for file url is below for 4HHB (hemoglobin).
```python
from rcsbsearchapi.search import StructSimilarityQuery

q3 = StructSimilarityQuery("file_url", "https://files.rcsb.org/view/4HHB.cif", input_option="cif")

# If using file upload, an example query would be like below:
# q3 = StructSimilarityQuery("file_upload", "absolute path to the file", input_option="file format")

list(q3())
```
