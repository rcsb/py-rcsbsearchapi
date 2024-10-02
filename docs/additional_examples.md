# Additional Examples

## Sequence Search Examples

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
## Sequence Motif Search Examples

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

results = SeqMotifQuery(
    "C.{2,4}C.{12}H.{3,5}H",
    pattern_type="regex",
    sequence_type="protein")

for polyid in results("polymer_entity"):
    print(polyid)
```

You can use a standard amino acid sequence to make a sequence motif search. 
X can be used to allow any amino acid in that position. 
As an example, here is a query for SH3 domains:
```python
from rcsbsearchapi.search import SeqMotifQuery

# The default pattern_type argument is "simple" and the sequence_type argument is "protein".
# X is used as a "variable residue" and can be any amino acid. 
results = SeqMotifQuery("XPPXP")

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
## Structure Similarity Search Examples

The PDB archive can be queried using the 3D shape of a protein structure. To perform this query, 3D protein structure data must be provided as an input or parameter, A chain ID or assembly ID must be specified, whether the input structure data should be compared to Assemblies or Polymer Entity Instance (Chains) is required, and defining the search type as either strict or relaxed is required. More information on how Structure Similarity Queries work can be found on the [RCSB PDB Structure Similarity Search](https://www.rcsb.org/docs/search-and-browse/advanced-search/structure-similarity-search) page.
```python
from rcsbsearchapi.search import StructSimilarityQuery

# Basic query:
# Querying using entry ID and default values assembly ID "1",
# operator "strict", target search space "Assemblies"
q1 = StructSimilarityQuery(entry_id="4HHB")

# Same example but with parameters explicitly specified
q1 = StructSimilarityQuery(
    structure_search_type="entry_id",
    entry_id="4HHB",
    structure_input_type="assembly_id",
    assembly_id="1",
    operator="strict_shape_match",
    target_search_space="assembly"
)
for rid in q1("assembly"):
    print(rid)
```
Below is a more complex example that utilizes chain ID, relaxed search operator, and polymer entity instance or target search space. Specifying whether the input structure
type is chain id or assembly id is very important. For example, specifying chain ID as the input structure type but inputting an assembly ID can lead to
an error.
```python
from rcsbsearchapi.search import StructSimilarityQuery

# More complex query:
# Entry ID value "4HHB", chain ID "B", operator "relaxed", and target search space "Chains"
q2 = StructSimilarityQuery(
    structure_search_type="entry_id",
    entry_id="4HHB",
    structure_input_type="chain_id",
    chain_id="B",
    operator="relaxed_shape_match",
    target_search_space="polymer_entity_instance"
)
list(q2())
```
Structure similarity queries also allow users to upload a file from their local computer or input a file url from the website to query the PDB archive for similar proteins. The file represents a target protein structure in the file formats "cif", "bcif", "pdb", "cif.gz", or "pdb.gz". If a user wants to use a file url for queries, the user must specify the structure search type, the value (being the url), and the file format of the file. This is also the same case for file upload, except the value is the absolute path leading to the file that is in the local machine. An example for file url is below for 4HHB (hemoglobin).
```python
from rcsbsearchapi.search import StructSimilarityQuery

q3 = StructSimilarityQuery(
    structure_search_type="file_url",
    file_url="https://files.rcsb.org/view/4HHB.cif",
    file_format="cif"
)
list(q3())

# To upload your own structure file, use the `file_path` parameter:
q4 = StructSimilarityQuery(
    structure_search_type="file_upload",
    file_path="/PATH/TO/FILE.cif",  # specify local model file path
    file_format="cif"
)
list(q4())
```

## Structure Motif Search Examples

The PDB Archive can also be queried by using a "motif" found in these 3D structures. To perform this type of query, an entry_id or a file URL/path must be provided, along with residues (which are parts of 3D structures.) This is the bare minimum needed to make a search, but there are lots of other parameters that can be added to a Structure Motif Query (see [full search schema](https://search.rcsb.org/redoc/index.html)).

To make a Structure Motif Query, you must first define anywhere from 2-10 "residues" that will be used in the query. Each individual residue has a Chain ID, Operator, Residue Number, and Exchanges (optional) that can be declared in that order using positonal arguments, or using the "chain_id", "struct_oper_id", and "label_seq_id" to define what parameter you are passing through. All 3 of the required parameters must be included, or the package will throw an AssertionError. 

Each residue can only have a maximum of 4 Exchanges, and each query can only have 16 exchanges total. Violating any of these rules will cause the package to throw an AssertionError. 

Examples of how to instantiate Residues can be found below. These can then be put into a list and passed through to a Structure Motif Query.
```python
from rcsbsearchapi.search import StructureMotifResidue

# Construct a Residue with a Chain ID of A, an operator of 1, a residue 
# number of 192, and Exchanges of "LYS" and "HIS"
Res1 = StructureMotifResidue("A", "1", 192, ["LYS", "HIS"])
# As for what is a valid "Exchange", the package provides these as a literal,
# and they should be type checked. 

# You can also specify the arguments:
# This query is the same as above. 
Res2 = StructureMotifResidue(
    struct_oper_id="1",
    chain_id="A",
    exchanges=["LYS", "HIS"],
    label_seq_id=192
)

# After declaring a minimum of 2 and as many as 10 residues,
# they can be passed into a list for use in the query itself:
Res3 = StructureMotifResidue("A", "1", 162)  # exchanges are optional

ResList = [Res1, Res3]
```
From there, these Residues can be used in a query. As stated before, you can only include 2 - 10 residues in a query. If you fail to provide residues for a query, or provide the wrong amount, the package will throw a ValueError. 

For a Structure Motif Query using an entry_id, the only other necessary value that must be passed into the query is the residue list. The default type of query is an entry_id query. 

As this type of query has a lot of optional parameters, do *not* use positional arguments as more than likely an error will occur. 

Below is an example of a basic entry_id Structure Motif Query, with the residues declared earlier:
```python
from rcsbsearchapi.search import StructMotifQuery

q1 = StructMotifQuery(entry_id="2MNR", residue_ids=ResList)
list(q1())
```
Like with Structure Similarity Queries, a file url or filepath can also be provided to the program. These can take the place of an entry_id. 

For a file url query, you *must* provide both a valid file URL (a string), and the file's file extension (also as a string). Failure to provide these elements correctly will cause the package to throw an AssertionError. 

Below is an example of the same query as above, only this time providing a file url:
```python
link = "https://files.rcsb.org/view/2MNR.cif"
q2 = StructMotifQuery(
    structure_search_type="file_url",
    url=link, file_extension="cif",
    residue_ids=ResList
)
# structure_search_type MUST be provided. A mismatched query type will cause an error. 
list(q2())
```
Like with Structure Similarity Queries, a filepath to a file may also be provided. This file must be a valid file accepted by the search API. A file extension must also be provided with the file upload. 

The query would look something like this:
```python
filepath = "/absolute/path/to/file.cif"
q3 = StructMotifQuery(
    structure_search_type="file_upload",
    file_path=filepath,
    file_extension="cif",
    residue_ids=ResList
)
list(q3())
```
There are many additional parameters that Structure Motif Query supports. These include a variety of features such as backbone distance tolerance, side chain distance tolerance, angle tolerance, RMSD cutoff, limits (stop searching after this many hits), atom pairing schemes, motif pruning strategy, allowed structures, and excluded structures. These can be mixed and matched as needed to make accurate and useful queries. All of these have some default value which is used when a parameter isn't provided. These parameters conform to the defaults used by the Search API. 

Below will demonstrate how to define these parameters using non-positional arguments:
```python
# specifying backbone distance tolerance: 0-3, default is 1
# allowed backbone distance tolerance in Angstrom. 
backbone = StructMotifQuery(
    entry_id="2MNR",
    backbone_distance_tolerance=2,
    residue_ids=ResList
)
list(backbone())

# specifying sidechain distance tolerance: 0-3, default is 1
# allowed side-chain distance tolerance in Angstrom.
sidechain = StructMotifQuery(
    entry_id="2MNR",
    side_chain_distance_tolerance=2,
    residue_ids=ResList
)
list(sidechain())

# specifying angle tolerance: 0-3, default is 1
# allowed angle tolerance in multiples of 20 degrees. 
angle = StructMotifQuery(
    entry_id="2MNR",
    angle_tolerance=2,
    residue_ids=ResList
)
list(angle())

# specifying RMSD cutoff: >=0, default is 2
# Threshold above which hits will be filtered by RMSD
rmsd = StructMotifQuery(
    entry_id="2MNR",
    rmsd_cutoff=1,
    residue_ids=ResList
)
list(rmsd())

# specifying limit: >=0, default excluded
# Stop accepting results after this many hits. 
limit = StructMotifQuery(
    entry_id="2MNR",
    limit=100,
    residue_ids=ResList
)
list(limit())

# specifying atom pairing scheme, default = "SIDE_CHAIN"
# ENUM: "ALL", "BACKBONE", "SIDE_CHAIN", "PSUEDO_ATOMS"
# this is typechecked by a literal. 
# Which atoms to consider to compute RMSD scores and transformations. 
atom = StructMotifQuery(
    entry_id="2MNR",
    atom_pairing_scheme="ALL",
    residue_ids=ResList
)
list(atom())

# specifying motif pruning strategy, default = "KRUSKAL"
# ENUM: "NONE", "KRUSKAL"
# this is typechecked by a literal in the package. 
# Specifies how many query motifs are "pruned".
# KRUSKAL leads to less stringent queries, and faster results.
pruning = StructMotifQuery(
    entry_id="2MNR",
    motif_pruning_strategy="NONE",
    residue_ids=ResList
)
list(pruning())

# specifying allowed structures, default excluded
# specify the structures you wish to allow in the return result. As an example,
# we could only allow the results from the limited query we ran earlier. 
allowed = StructMotifQuery(
    entry_id="2MNR",
    allowed_structures=list(limit()),
    residue_ids=ResList
)
list(allowed())

# specifying structures to exclude, default excluded
# specify structures to exclude from a query. We could, for example,
# exclude the results of the previous allowed query. 
excluded = StructMotifQuery(
    entry_id="2MNR",
    excluded_structures=list(allowed()),
    residue_ids=ResList
)
list(excluded())
```
The Structure Motif Query can be used to make some very specific queries. Below is an example of a query that retrives occurances of the enolase superfamily, a group of proteins diverse in sequence and structure that are all capable of abstracting a proton from a carboxylic acid. Position-specific exchanges are crucial to represent this superfamily accurately.
```python
Res1 = StructureMotifResidue("A", "1", 162, ["LYS", "HIS"])
Res2 = StructureMotifResidue("A", "1", 193)
Res3 = StructureMotifResidue("A", "1", 219)
Res4 = StructureMotifResidue("A", "1", 245, ["GLU", "ASP", "ASN"])
Res5 = StructureMotifResidue("A", "1", 295, ["HIS", "LYS"])

ResList = [Res1, Res2, Res3, Res4, Res5]

query = StructMotifQuery(entry_id="2MNR", residue_ids=ResList)

list(query())
```
## Chemical Similarity Search Examples

When you have unique chemical information (e.g., a chemical formula or descriptor) you can use this information to find chemical components (e.g., drugs, inhibitors, modified residues, or building blocks such as amino acids, nucleotides, or sugars), so that it is similar to the formula or descriptor used in the query (perhaps one or two atoms/groups are different), is part of a larger molecule (i.e., the specified formula/descriptor is a substructure), or is exactly or very closely matches the formula or descriptor used in the query. 

The search can also be used to identify PDB structures that include the chemical component(s) which match or are similar to the query. These structures can then be examined to learn about the interactions of the component within the structure. More information on Chemical Similarity Queries can be found on the [RCSB PDB Chemical Similarity Search](https://www.rcsb.org/docs/search-and-browse/advanced-search/chemical-similarity-search) page.

To do a Chemical Similarity query, you must first specify one of two possible query options which are formula and descriptors. Formula allows queries to be made by providing a chemical formula. Descriptors allow you to search by chemical notations for example. Each Query option has its own distinct set of parameters, but both options require a value.

The formula query option comes with a match subset parameter which allows users to search chemical components whose formula exactly match the query or matches any portion of the query. The descriptor query option comes with a descriptor type parameter and match type parameter. The descriptor type parameter specifies what type of descriptor the input value is. There are two options which are SMILES (Simplified Molecular Input Line Entry Specification) and InChI (International Chemical Identifier). The match type parameter has six options which are Similar Ligands (Quick Screen), Similar Ligands (Stereospecific), Similar Ligands (including Stereoisomers), Substructure (Stereospecific), Substructure (including Stereoisomers), and Exact match.

When doing Chemical Similarity Queries in this tool, it is important to note that by default the query option is set to formula and match subset is set to False. An example of how that looks like is below.
```python
from rcsbsearchapi.search import ChemSimilarityQuery

# Basic query with default values: query type = formula and match subset = False
q1 = ChemSimilarityQuery(value="C12 H17 N4 O S")

# Same example but with all the parameters listed
q1 = ChemSimilarityQuery(
    value="C12 H17 N4 O S",
    query_type="formula",
    match_subset=False
)
list(q1())
```
Below is are two examples of using query option descriptor. Both descriptor type parameters are also used.
```python
from rcsbsearchapi.search import ChemSimilarityQuery

# Query with type = descriptor, descriptor type = SMILES,
# match type = similar ligands (sterospecific) or graph-relaxed-stereo
q2 = ChemSimilarityQuery(
    value="Cc1c(sc[n+]1Cc2cnc(nc2N)C)CCO",
    query_type="descriptor",
    descriptor_type="SMILES",
    match_type="graph-relaxed-stereo"
)
list(q2())
```
```python
from rcsbsearchapi.search import ChemSimilarityQuery

# Query with type = descriptor, descriptor type = InChI,
# match type = substructure (sterospecific) or sub-struct-graph-relaxed-stereo
q3 = ChemSimilarityQuery(
    value="InChI=1S/C13H10N2O4/c16-10-6-5-9(11(17)14-10)15-12(18)7-3-1-2-4-8(7)13(15)19/h1-4,9H,5-6H2,(H,14,16,17)/t9-/m0/s1",
    query_type="descriptor",
    descriptor_type="InChI",
    match_type="sub-struct-graph-relaxed-stereo"
)
list(q3())
```
## Faceted Query Examples
For more details on arguments, see the [API reference](api.rst)

In order to group and perform calculations and statistics on PDB data by using a simple search query, you can use a faceted query (or facets). Facets arrange search results into categories (buckets) based on the requested field values. More information on Faceted Queries can be found [here](https://search.rcsb.org/#using-facets). All facets should be provided with `name`, `aggregation_type`, and `attribute` values. Depending on the aggregation type, other parameters must also be specified. The `facets()` function runs the query `q` using the specified facet(s), and returns a list of dictionaries:
```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi.search import Facet

q = AttributeQuery(
    attribute="rcsb_accession_info.initial_release_date",
    operator="greater",
    value="2019-08-20"
)
q(facets=Facet(name="Methods", aggregation_type="terms", attribute="exptl.method")).facets
```

### Terms Facets
Terms faceting is a multi-bucket aggregation where buckets are dynamically built - one per unique value. We can specify the minimum count (`>= 0`) for a bucket to be returned using the parameter `min_interval_population` (default value `1`). We can also control the number of buckets returned (`<= 65336`) using the parameter `max_num_intervals` (default value `65336`).
```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi.search import Facet

# This is the default query used by the RCSB Search API when no query is specified.
# This default query will be used for most of the examples found below for faceted queries.
q = AttributeQuery(
    attribute="rcsb_entry_info.structure_determination_methodology",
    operator="exact_match",
    value="experimental",
) 

q(
    facets= Facet(
        name="Journals",
        aggregation_type="terms",
        attribute="rcsb_primary_citation.rcsb_journal_abbrev",
        min_interval_population=1000
    )
).facets
```

### Histogram Facets
Histogram facets build fixed-sized buckets (intervals) over numeric values. The size of the intervals must be specified in the parameter `interval`. We can also specify `min_interval_population` if desired.
```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi.search import Facet

q = AttributeQuery(
    attribute="rcsb_entry_info.structure_determination_methodology",
    operator="exact_match",
    value="experimental"
) 

q(
    return_type="polymer_entity",
    facets=Facet(
        name="Formula Weight",
        aggregation_type="histogram",
        attribute="rcsb_polymer_entity.formula_weight",
        interval=50,
        min_interval_population=1
    )
).facets
```

### Date Histogram Facets
Similar to histogram facets, date histogram facets build buckets over date values. For date histogram aggregations, we must specify `interval="year"`. Again, we may also specify `min_interval_population`.
```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi.search import Facet

q = AttributeQuery(
    attribute="rcsb_entry_info.structure_determination_methodology",
    operator="exact_match",
    value="experimental"
) 

q(
    facets=Facet(
        name="Release Date",
        aggregation_type="date_histogram",
        attribute="rcsb_accession_info.initial_release_date",
        interval="year",
        min_interval_population=1
    )
).facets
```

### Range Facets
We can define the buckets ourselves by using range facets. In order to specify the ranges, we use the `Range` class. Note that the range includes the `start` value and excludes the `end` value (`include_lower` and `include_upper` should not be specified). If the `start` or `end` is omitted, the minimum or maximum boundaries will be used by default. The buckets should be provided as a list of `Range` objects to the `ranges` parameter.  
```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi.search import Facet, Range

q = AttributeQuery(
    attribute="rcsb_entry_info.structure_determination_methodology",
    operator="exact_match",
    value="experimental"
)

q(
    facets=Facet(
        name="Resolution Combined",
        aggregation_type="range",
        attribute="rcsb_entry_info.resolution_combined",
        ranges=[
            Range(start=None,end=2),
            Range(start=2, end=2.2),
            Range(start=2.2, end=2.4),
            Range(start=4.6, end=None)
        ]
    )
).facets
```

### Date Range Facets
Date range facets allow us to specify date values as bucket ranges, using [date math expressions](https://search.rcsb.org/#date-math-expressions).
```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi.search import Facet, Range

q = AttributeQuery(
    attribute="rcsb_entry_info.structure_determination_methodology",
    operator="exact_match",
    value="experimental"
)

q(
    facets=Facet(
        name="Release Date",
        aggregation_type="date_range",
        attribute="rcsb_accession_info.initial_release_date",
        ranges=[
            Range(start=None,end="2020-06-01||-12M"),
            Range(start="2020-06-01", end="2020-06-01||+12M"),
            Range(start="2020-06-01||+12M", end=None)
        ]
    )
).facets
```

### Cardinality Facets 
Cardinality facets return a single value: the count of distinct values returned for a given field. A `precision_threshold` (`<= 40000`, default value `40000`) may be specified.
```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi.search import Facet

q = AttributeQuery(
    attribute="rcsb_entry_info.structure_determination_methodology",
    operator="exact_match",
    value="experimental",
) 

q(
    facets=Facet(
        name="Organism Names Count",
        aggregation_type="cardinality",
        attribute="rcsb_entity_source_organism.ncbi_scientific_name"
    )
).facets
```

### Multidimensional Facets
Complex, multi-dimensional aggregations are possible by specifying additional facets in the `nested_facets` parameter, as in the example below:
```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi.search import Facet

f1 = Facet(
    name="Polymer Entity Types",
    aggregation_type="terms",
    attribute="rcsb_entry_info.selected_polymer_entity_types"
)
f2 = Facet(
    name="Release Date",
    aggregation_type="date_histogram",
    attribute="rcsb_accession_info.initial_release_date",
    interval="year"
)

q = AttributeQuery(
    attribute="rcsb_entry_info.structure_determination_methodology",
    operator="exact_match",
    value="experimental",
) 

q(
    facets=Facet(
        name="Experimental Method",
        aggregation_type="terms",
        attribute="rcsb_entry_info.experimental_method",
        nested_facets=[f1, f2]
    )
).facets
```

### Filter Facets
Filters allow us to filter documents that contribute to bucket count. Similar to queries, we can group several `TerminalFilter`s into a single `GroupFilter`. We can combine a filter with a facet using the `FilterFacet` class. Terminal filters should specify an `attribute` and `operator`, as well as possible a `value` and whether or not it should be a `negation` and/or `case_sensitive`. Group filters should specify a `logical_operator` (which should be either `"and"` or `"or"`) and a list of filters (`nodes`) that should be combined. Finally, the `FilterFacet` should be provided with a filter and a (list of) facet(s). Here are some examples:
```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi.search import TerminalFilter, GroupFilter, FilterFacet, Facet

tf1 = TerminalFilter(
    attribute="rcsb_polymer_instance_annotation.type",
    operator="exact_match",
    value="CATH"
)
tf2 = TerminalFilter(
    attribute="rcsb_polymer_instance_annotation.annotation_lineage.id",
    operator="in",
    value=["2.140.10.30", "2.120.10.80"]
)
ff2 = FilterFacet(
    filter=tf2,
    facets=Facet(
        name="CATH Domains",
        aggregation_type="terms",
        attribute="rcsb_polymer_instance_annotation.annotation_lineage.id",
        min_interval_population=1
    )
)

q = AttributeQuery(
    attribute="rcsb_entry_info.structure_determination_methodology",
    operator="exact_match",
    value="experimental"
) 

q(
    return_type="polymer_instance",
    facets=FilterFacet(filter=tf1, facets=ff2
)).facets
```
```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi.search import TerminalFilter, GroupFilter, FilterFacet, Facet

tf1 = TerminalFilter(
    attribute="rcsb_struct_symmetry.kind",
    operator="exact_match",
    value="Global Symmetry",
    negation=False
)
f2 = Facet(
    name="ec_terms",
    aggregation_type="terms",
    attribute="rcsb_polymer_entity.rcsb_ec_lineage.id"
)
f1 = Facet(
    name="sym_symbol_terms",
    aggregation_type="terms",
    attribute="rcsb_struct_symmetry.symbol",
    nested_facets=f2
)

ff = FilterFacet(filter=tf1, facets=f1)
q1 = AttributeQuery(
    attribute="rcsb_assembly_info.polymer_entity_count",
    operator="equals",
    value=1
)
q2 = AttributeQuery(
    attribute="rcsb_assembly_info.polymer_entity_instance_count",
    operator="greater",
    value=1
)
q = q1 & q2
q(return_type="assembly", facets=ff).facets
```
```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi.search import TerminalFilter, GroupFilter, FilterFacet, Facet

tf1 = TerminalFilter(
    attribute="rcsb_polymer_entity_group_membership.aggregation_method",
    operator="exact_match",
    value="sequence_identity"
)
tf2 = TerminalFilter(
    attribute="rcsb_polymer_entity_group_membership.similarity_cutoff",
    operator="equals",
    value=100)
gf = GroupFilter(logical_operator="and", nodes=[tf1, tf2])
ff = FilterFacet(
    filter=gf,
    facets=Facet(
        "Distinct Protein Sequence Count",
        "cardinality",
        "rcsb_polymer_entity_group_membership.group_id"
    )
)
q = AttributeQuery(
    attribute="rcsb_assembly_info.polymer_entity_count",
    operator="equals",
    value=1,
)
q(return_type="polymer_entity", facets=ff).facets
```

## GroupBy Example
For more details on arguments to create `RequestOption` objects, see the [API reference](api.rst).

Sequence Identity and Matching Uniprot Accession examples from [Search API Documentation](https://search.rcsb.org/#group-by-return-type).

### Matching Deposit Group ID
Grouping on the basis of common identifier for a group of entries deposited as a collection.

This example searches for entries associated with "interleukin" from humans with investigational or experimental drugs bound.
Since group_by_return_type is specified as "representatives", one representative structure per group is returned.

```python
from rcsbsearchapi import AttributeQuery, TextQuery
from rcsbsearchapi import rcsb_attributes as attrs
from rcsbsearchapi.search import GroupBy

q1 = TextQuery("interleukin")
q2 = attrs.rcsb_entity_source_organism.scientific_name == "Homo sapiens"
q3 = attrs.drugbank_info.drug_groups == "investigational"
q4 = attrs.drugbank_info.drug_groups == "experimental"

query = q1 & q2 & (q3 | q4)
list(
    query(
        group_by=GroupBy(aggregation_method="matching_deposit_group_id"),
        group_by_return_type="representatives"  # only a single search hit is returned per group
    )
)
```

### Sequence Identity
The method used to group search hits on the basis of protein sequence clusters that meet a predefined identity threshold.

This example groups together identical human sequences from high-resolution (1.0-2.0Å) structures determined by X-ray crystallography. Among the resulting groups, there is a cluster of human glutathione transferases in complex with different substrates.
```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi import rcsb_attributes as attrs
from rcsbsearchapi.search import GroupBy, RankingCriteriaType

q1 = attrs.rcsb_entity_source_organism.taxonomy_lineage.name == "Homo sapiens"
q2 = attrs.exptl.method == "X-RAY DIFFRACTION"
q3 = attrs.rcsb_entry_info.resolution_combined >= 1
q4 = attrs.rcsb_entry_info.resolution_combined <= 2

query = q1 & q2 & q3 & q4

list(query(
    return_type="polymer_entity", # "sequence_identity" must use return type "polymer_entity"
    group_by=GroupBy(
        aggregation_method="sequence_identity",
        similarity_cutoff=100,  # 100, 95, 90, 70, 50, or 30
        ranking_criteria_type=RankingCriteriaType(
                sort_by="entity_poly.rcsb_sample_sequence_length",
                direction="desc"
        )
    ),
    group_by_return_type="groups"  # divide into groups returned with all associated hits
))
```

### Matching Uniprot Accession
This example demonstrates how to use `matching_uniprot_accession` grouping to get distinct Spike protein S1 proteins released from the beginning of 2020 with. Here, all entities are represented by distinct groups of SARS-CoV, SARS-CoV-2 and Pangolin coronavirus spike proteins.

```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi import rcsb_attributes as attrs
from rcsbsearchapi.search import GroupBy, RankingCriteriaType

q1 = AttributeQuery(
    attribute="rcsb_polymer_entity.pdbx_description",
    operator="contains_phrase",
    value="Spike protein S1"
)
q2 = attrs.rcsb_accession_info.initial_release_date > "2020-01-01"

query = q1 & q2
list(query(
    return_type="polymer_entity",  # "matching_uniprot_accession" must use return type "polymer_entity"
    group_by=GroupBy(
        aggregation_method="matching_uniprot_accession",
        ranking_criteria_type= RankingCriteriaType(
            sort_by="coverage"
        )
    ),
    group_by_return_type="groups"
))
```

## Sort Example
The `sort` request option can be used to control sorting of results. By default, results are sorted by "score" in descending order.
You can also sort by attribute name and apply filters.

Example from [RCSB PDB Search API](https://search.rcsb.org/#sorting) page.

```python
from rcsbsearchapi import AttributeQuery
from rcsbsearchapi.search import Sort

query = AttributeQuery(
    attribute="struct.title",
    operator="contains_phrase",
    value="hiv protease",
)

list(query(sort=
    Sort(
        sort_by="rcsb_accession_info.initial_release_date",
        direction="desc"
    )
))
```