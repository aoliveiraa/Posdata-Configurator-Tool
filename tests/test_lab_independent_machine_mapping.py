import unittest

from src.discovery.lab_independent_machine_mapping import (
    normalize_pos_node,
    resolve_all_target_machines,
    resolve_machine_for_target,
)


CURRENT = [
    {"node": "POS0001", "file": "_JS970WS_pos-db.xml", "ip": "10.118.57.1"},
    {"node": "POS0002", "file": "_NCRXR7PR77_pos-db.xml", "ip": "10.118.57.11"},
    {"node": "POS0003", "file": "_NCRXR7W10_pos-db.xml", "ip": "10.118.57.2"},
    {"node": "POS0004", "file": "_NCRXR7PR7_pos-db.xml", "ip": "10.118.57.12"},
]

TARGETS = [
    {"node": "POS0001", "machine_ip": "10.118.51.1", "output_file": "_RENEIGHPOS01_pos-db.xml"},
    {"node": "POS0002", "machine_ip": "10.118.51.3", "output_file": "_RENEIGHPOS03_pos-db.xml"},
    {"node": "POS0003", "machine_ip": "10.118.51.2", "output_file": "_RENEIGHPOS02_pos-db.xml"},
    {"node": "POS0004", "machine_ip": "10.118.51.12", "output_file": "_RENEIGHPOS12_pos-db.xml"},
]


class LabIndependentMachineMappingTests(unittest.TestCase):
    def test_normalize_node(self):
        self.assertEqual(normalize_pos_node("pos1"), "POS0001")
        self.assertEqual(normalize_pos_node("POS01"), "POS0001")
        self.assertIsNone(normalize_pos_node("KVS0001"))

    def test_resolves_by_node_not_ip(self):
        result = resolve_machine_for_target(TARGETS[0], CURRENT)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["current_machine_file"], "_JS970WS_pos-db.xml")
        self.assertEqual(result["current_machine_ip"], "10.118.57.1")
        self.assertEqual(result["target_machine_ip"], "10.118.51.1")
        self.assertEqual(result["source"], "logical_node")

    def test_all_targets_ready_across_different_subnets(self):
        result = resolve_all_target_machines(TARGETS, CURRENT)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["ready"], 4)

    def test_missing_node(self):
        target = {"node": "POS0099", "machine_ip": "10.118.51.99", "output_file": "x.xml"}
        result = resolve_machine_for_target(target, CURRENT)
        self.assertEqual(result["status"], "MISSING")
        self.assertIn("POS0099", result["warnings"][0])

    def test_duplicate_node_requires_review(self):
        current = CURRENT + [{"node": "POS0001", "file": "duplicate.xml", "ip": "10.0.0.1"}]
        result = resolve_machine_for_target(TARGETS[0], current)
        self.assertEqual(result["status"], "REVIEW REQUIRED")

    def test_target_ip_is_required_but_not_used_for_lookup(self):
        target = {"node": "POS0001", "output_file": "x.xml"}
        result = resolve_machine_for_target(target, CURRENT)
        self.assertEqual(result["current_machine_file"], "_JS970WS_pos-db.xml")
        self.assertEqual(result["status"], "MISSING")
        self.assertTrue(any("Target lab IP" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
