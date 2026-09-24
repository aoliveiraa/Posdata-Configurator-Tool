from types import SimpleNamespace

from src.builder.builder_assignment_phase import (
    confirm_itona_assignments,
    confirm_pos_assignments,
)


def _pos_context():
    return SimpleNamespace(
        discovered_pos={"pos_files": [
            {"file": "_POS01.xml", "path": "p1", "role": "FC", "role_confidence": "HIGH", "node_candidates": ["POS0001"]},
            {"file": "_POS02.xml", "path": "p2", "role": "FC", "role_confidence": "HIGH", "node_candidates": ["POS0002"]},
            {"file": "_POS03.xml", "path": "p3", "role": "FC", "role_confidence": "HIGH", "node_candidates": ["POS0003"]},
        ]},
        proposed_pos_mapping={
            "assignments": [
                {"target_node": "POS0001", "target_role": "FC", "source_file": "_POS01.xml"},
                {"target_node": "POS0002", "target_role": "FC", "source_file": "_POS02.xml"},
                {"target_node": "POS0003", "target_role": "DT", "source_file": None},
            ],
            "extra_candidates": [{"file": "_POS03.xml", "role": "FC"}],
        },
        confirmed_pos_mapping={},
    )


def test_fc_can_replace_dt_lab_suggestion():
    context = _pos_context()
    result = confirm_pos_assignments(
        context,
        {"POS0001": "_POS01.xml", "POS0002": "_POS02.xml", "POS0003": "_POS03.xml"},
        {},
    )
    assert not result["errors"]
    third = result["assignments"][2]
    assert third["expected_role"] == "DT"
    assert third["effective_role"] == "FC"
    assert third["target_role"] == "FC"


def test_same_pos_cannot_be_reused():
    context = _pos_context()
    result = confirm_pos_assignments(
        context,
        {"POS0001": "_POS01.xml", "POS0002": "_POS01.xml", "POS0003": "_POS03.xml"},
        {"_POS02.xml": "IGNORE"},
    )
    assert result["status"] == "FAIL"
    assert any("cannot be reused" in error for error in result["errors"])


def _itona_context():
    return SimpleNamespace(
        discovered_itona_candidates=[
            {"file": "_KVS1.xml", "path": "k1", "kvs_types": ["OAT"], "kvs_services": ["1001"]},
            {"file": "_KVS2.xml", "path": "k2", "kvs_types": ["OAT"], "kvs_services": ["1002"]},
            {"file": "_KVS3.xml", "path": "k3", "kvs_types": ["OAT"], "kvs_services": ["1003"]},
        ],
        proposed_itona_mapping={"assignments": [{"slot": "Itona1", "source_file": "_KVS1.xml"}]},
        confirmed_itona_mapping={},
    )


def test_maximum_two_kvs_per_itona():
    context = _itona_context()
    result = confirm_itona_assignments(
        context,
        {"Itona1": ["_KVS1.xml", "_KVS2.xml", "_KVS3.xml"]},
    )
    assert result["status"] == "FAIL"
    assert "maximum of 2" in result["errors"][0]
