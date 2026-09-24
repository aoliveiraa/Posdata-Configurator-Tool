PosData Builder Sprint 1.5.2

Changes:
- POS role filtering removed.
- Any POS source can occupy any target POS slot.
- Effective role follows selected source.
- Lab role retained as expected_role.
- Extra POS selected in a slot is automatically assigned.
- Maximum 2 KVS per Itona enforced in business logic and UI.

Tests:
python -m pytest tests/test_builder_flexible_pos.py

Run:
python builder_ui.py
