from types import SimpleNamespace

from src.builder.builder_assignment_phase import confirm_pos_assignments


def _context():
    return SimpleNamespace(
        discovered_pos={
            "pos_files": [
                {
                    "file": "_POS01.xml",
                    "path": "source/_POS01.xml",
                    "role": "FC",
                    "role_confidence": "HIGH",
                    "role_status": "READY",
                    "node_candidates": ["POS0001"],
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
        proposed_pos_mapping={
            "assignments": [
                {
                    "target_node": "POS0001",
                    "target_role": "FC",
                    "source_file": "_POS01.xml",
                }
            ],
            "extra_candidates": [],
        },
        confirmed_pos_mapping={},
    )


def test_confirm_pos_assignment():
    context = _context()
    result = confirm_pos_assignments(
        context,
        {"POS0001": "_POS01.xml"},
        {},
    )
    assert result["status"] == "READY"
    assert result["assignments"][0]["source_file"] == "_POS01.xml"


def test_none_is_allowed():
    context = _context()
    result = confirm_pos_assignments(
        context,
        {"POS0001": "NONE"},
        {},
    )
    assert result["status"] == "READY WITH SKIPS"
    assert result["assignments"][0]["status"] == "SKIPPED"
