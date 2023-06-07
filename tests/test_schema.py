from rcsbsearchapi import rcsb_attributes as attrs


def test_schema():
    assert attrs.rcsb_id.attribute == "rcsb_id"

    assert attrs.rcsb_struct_symmetry.symbol.attribute == "rcsb_struct_symmetry.symbol"
