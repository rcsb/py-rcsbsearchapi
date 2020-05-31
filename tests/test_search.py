from rcsbsearch import Terminal, Group, Session
import requests

# q1 = rcsb.Terminal("rcsb_struct_symmetry.type", "exact_match", "Icosahedral")
# q2 = rcsb.Terminal("rcsb_struct_symmetry.kind", "exact_match", "Global Symmetry")


def test_construction():
    q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ['4HHB', '2GS2'])
    q2 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ['4HHB', '5T89'])

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


def test_single():
    q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ['4HHB', '2GS2'])
    session = Session(Group("and", [q1]))
    result = session._single_query()
    assert result is not None


def test_iquery():
    q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ['4HHB', '2GS2'])
    session = Session(q1)
    result = session.iquery()
    assert len(result) == 2


def test_iter():
    ids =['4HHB', '2GS2']
    q1 = Terminal("rcsb_entry_container_identifiers.entry_id", "in", ids)
    session = Session(q1)
    result = set(session)
    assert len(result) == 2
    assert result == set(ids)

def test_pagination():
    ids =['4HHB', '2GS2', '5T89', '1TIM']
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

def test_errors():
    # Malformed
    q1 = Terminal("invalid_identifier", "exact_match", "ERROR")
    session = Session(q1)
    try:
        result = set(session)
        assert False, "Should raise error"
    except requests.HTTPError as e:
        pass

