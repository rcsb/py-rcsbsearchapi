from rcsbsearch import Terminal, Group, Session, Attr, Value
import requests
import pytest  # type: ignore

# q1 = rcsb.Terminal("rcsb_struct_symmetry.type", "exact_match", "Icosahedral")
# q2 = rcsb.Terminal("rcsb_struct_symmetry.kind", "exact_match", "Global Symmetry")


def test_construction():
    q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["4HHB", "2GS2"])
    q2 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["4HHB", "5T89"])

    both = q1 & q2
    assert isinstance(both, Group)
    assert both.operator == "and"
    assert both.nodes[0] == q1
    assert both.nodes[1] == q2

    either = q1 | q2
    assert isinstance(either, Group)
    assert either.operator == "or"
    assert either.nodes[0] == q1
    assert either.nodes[1] == q2


@pytest.mark.internet
def test_single():
    q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["4HHB", "2GS2"])
    session = Session(Group("and", [q1]))
    result = session._single_query()
    assert result is not None


@pytest.mark.internet
@pytest.mark.progressbar
def test_iquery():
    q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["4HHB", "2GS2"])
    session = Session(q1)
    result = session.iquery()
    assert len(result) == 2


@pytest.mark.internet
def test_iter():
    ids = ["4HHB", "2GS2"]
    q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ids)
    result = set(q1())
    assert len(result) == 2
    assert result == set(ids)


@pytest.mark.internet
def test_inv():
    q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "exact_match", "5T89")
    q = ~q1
    # Lots of results
    first = next(iter(q()))
    assert first is not None
    assert first != "5T89"


@pytest.mark.internet
def test_xor():
    ids1 = ["5T89", "2GS2"]
    ids2 = ["4HHB", "2GS2"]
    q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ids1)
    q2 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ids2)
    q = q1 ^ q2
    print(f"XOR Query: {q}")
    result = set(q())
    assert len(result) == 2
    assert result == {ids1[0], ids2[0]}


@pytest.mark.internet
def test_pagination():
    ids = ["4HHB", "2GS2", "5T89", "1TIM"]
    q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ids)

    # 2+2 results
    session = Session(q1, rows=2)
    result = set(session)
    assert len(result) == 4
    assert result == set(ids)

    # 3+1 results
    session = Session(q1, rows=3)
    result = set(session)
    assert len(result) == 4
    assert result == set(ids)

    # 1ABC will never be a valid ID
    q2 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ["1ABC"])
    session = Session(q2)
    result = set(session)
    assert len(result) == 0


@pytest.mark.internet
def test_errors():
    # Malformed
    q1 = Terminal("invalid_identifier", "exact_match", "ERROR")
    session = Session(q1)
    try:
        set(session)
        assert False, "Should raise error"
    except requests.HTTPError:
        pass


@pytest.mark.internet
def test_example1():
    "'Biological Assembly Search' from http://search.rcsb.org/#examples"
    q1 = Terminal("rcsb_struct_symmetry.symbol", "exact_match", "C2")
    q2 = Terminal("rcsb_struct_symmetry.kind", "exact_match", "Global Symmetry")
    q3 = Terminal(value='"heat-shock transcription factor"')
    q4 = Terminal("rcsb_entry_info.polymer_entity_count_DNA", "greater_or_equal", 1)
    q = q1 & q2 & q3 & q4  # AND of all queries

    results = set(q("assembly"))
    assert len(results) > 0  # 14 results 2020-06
    assert "1FYL-1" in results


@pytest.mark.internet
def test_example2():
    "'X-Ray Structures Search' from http://search.rcsb.org/#examples"
    q = (
        Terminal(value='"thymidine kinase"')
        & Terminal(
            "rcsb_entity_source_organism.taxonomy_lineage.name",
            "exact_match",
            "Viruses",
        )
        & Terminal("exptl.method", "exact_match", "X-RAY DIFFRACTION",)
        & Terminal("rcsb_entry_info.resolution_combined", "less_or_equal", 2.5,)
        & Terminal("rcsb_entry_info.nonpolymer_entity_count", "greater", 0)
    )

    results = set(q("entry"))
    assert len(results) > 0  # 224 results 2020-06
    assert "1KI6" in results


def test_attr():
    attr = Attr("attr")

    term = attr == "value"
    assert isinstance(term, Terminal)
    assert term.operator == "exact_match"

    term = "value" == attr
    assert isinstance(term, Terminal)
    assert term.operator == "exact_match"

    term = Value("value") == attr
    assert isinstance(term, Terminal)
    assert term.operator == "exact_match"
