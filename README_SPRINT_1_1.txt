PosData Builder - Sprint 1.1

Included:
- BuilderContext
- Internal TemplateRepository
- Builder input validation
- Initial builder entry point
- Template repository tests

Expected repository folders:
- templates/AU
- templates/CA
- templates/DE
- templates/PT
- templates/UK
- templates/US

Run tests:
python -m pytest tests/test_template_repository.py

Smoke test:
python builder.py
