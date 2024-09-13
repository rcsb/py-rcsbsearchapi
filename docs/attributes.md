# Attributes

Attributes are pieces of information associated with a PDB structure that can be searched for or compared to a value using an [`AttributeQuery`](quickstart.md#getting-started)
There are structure attributes and chemical attributes, which are both stored in `rcsb_attributes`. This can be imported as shown below:

```python
# you can import rcsb_attributes as attrs for a shorter name
from rcsbsearchapi import rcsb_attributes as attrs
```

There are several helpful methods for searching for attributes and information related to them.

###search()
Given a string, this method will return an iterable of `Attr` objects with names that contain the given string. You can also use [regular expression (regex)](https://en.wikipedia.org/wiki/Regular_expression) strings.

```python
matching_attrs = attrs.search("author")

for attr in matching_attrs:
    print(attr)
```

###get_attribute_details()
Given a full or partial attribute name, return a set of an attribute or associated attributes with attribute names, search service types, and descriptions.

```python
from rcsbsearchapi import rcsb_attributes as attrs

# Use a full name to get details for a specific attribute
print(attrs.get_attribute_details("rcsb_entity_source_organism.scientific_name"))

# Use a partial name to get details of all attributes associate with that partial name
# The below code prints out details for ".common_name", ".ncbi_parent_scientific_name", etc in addition to ".scientific_name"
print(attrs.get_attribute_details("rcsb_entity_source_organism"))
```

###get_attribute_type()
Given a full attribute name, return the search service type ("text" for structure attributes and "text_chem" for chemical attributes).

```python
from rcsbsearchapi import rcsb_attributes as attrs
 
print(attrs.get_attribute_type("rcsb_entity_source_organism.scientific_name"))
```