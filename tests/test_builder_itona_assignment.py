from types import SimpleNamespace
from src.builder.builder_assignment_phase import confirm_itona_assignments


def _context():
    return SimpleNamespace(
        discovered_itona_candidates=[
            {"file": "_KVS1.xml", "path": "p1", "kvs_types": ["OAT"], "kvs_services": ["1001"]},
            {"file": "_KVS2.xml", "path": "p2", "kvs_types": ["PRESENTATION"], "kvs_services": ["1002"]},
            {"file": "_KVS3.xml", "path": "p3", "kvs_types": ["UNKNOWN"], "kvs_services": ["1003"]},
        ],
        proposed_itona_mapping={
            "assignments": [
                {"slot": "Itona1", "source_file": "_KVS1.xml"},
                {"slot": "Itona2", "source_file": "_KVS2.xml"},
            ]
        },
        confirmed_itona_mapping={},
    )


def test_itona_accepts_multiple_kvs():
    context = _context()
    result = confirm_itona_assignments(
        context,
        {"Itona1": ["_KVS1.xml", "_KVS2.xml"], "Itona2": []},
    )
    assert result["status"] == "READY WITH SKIPS"
    assert result["assignments"][0]["source_files"] == ["_KVS1.xml", "_KVS2.xml"]
    assert result["assignments"][0]["kvs_services"] == ["1001", "1002"]


def test_kvs_cannot_be_reused():
    context = _context()
    result = confirm_itona_assignments(
        context,
        {"Itona1": ["_KVS1.xml"], "Itona2": ["_KVS1.xml"]},
    )
    assert result["status"] == "FAIL"
    assert "cannot also be assigned" in result["errors"][0]


def test_unknown_is_allowed_after_manual_selection():
    context = _context()
    result = confirm_itona_assignments(
        context,
        {"Itona1": ["_KVS3.xml"], "Itona2": ["_KVS2.xml"]},
    )
    assert result["status"] == "READY WITH OBSERVATIONS"
