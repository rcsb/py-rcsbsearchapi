# rcsbsearch

Python interface for the RCSB search API.

Currently the 'text search' part of the API has been implemented.

This package requires python 3.7 or later.

## Example

Here is a quick example of how the package is used:

    from rcsbsearch import Terminal

    # Create terminals for each query
    q1 = Terminal(value='"heat-shock transcription factor"')
    q2 = Terminal("rcsb_struct_symmetry.symbol", "exact_match", "C2")
    q3 = Terminal("rcsb_struct_symmetry.kind", "exact_match", "Global Symmetry")
    q4 = Terminal("rcsb_entry_info.polymer_entity_count_DNA", "greater_or_equal", 1)

    # combined using bitwise operators (&, |, ~, etc)
    query = q1 & q2 & q3 & q4  # AND of all queries

    # Call the query to execute it
    for pdbid in query():
        print(pdbid)

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
