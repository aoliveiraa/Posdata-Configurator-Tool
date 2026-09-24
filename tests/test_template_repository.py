from pathlib import Path

from src.builder.template_repository import TemplateRepository


def test_lists_only_supported_existing_templates(tmp_path: Path):
    (tmp_path / "CA").mkdir()
    (tmp_path / "ES").mkdir()
    repository = TemplateRepository(tmp_path)
    assert repository.available_templates() == ["CA"]


def test_template_requires_store_screen_and_posdb(tmp_path: Path):
    folder = tmp_path / "CA"
    folder.mkdir()
    (folder / "store-db.xml").write_text("<StoreDB/>", encoding="utf-8")
    (folder / "screen.xml").write_text("<Screens/>", encoding="utf-8")
    (folder / "_POS0001_pos-db.xml").write_text("<PosDB/>", encoding="utf-8")
    result = TemplateRepository(tmp_path).validate("CA")
    assert result["status"] == "READY"
