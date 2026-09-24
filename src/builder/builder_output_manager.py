from pathlib import Path
import shutil


DEFAULT_OUTPUT_FOLDER = Path(
    "output_builder"
)


def build_output_paths(
    base_folder=DEFAULT_OUTPUT_FOLDER
):
    base_folder = Path(
        base_folder
    )

    return {
        "root": base_folder,
        "storedb": (
            base_folder
            / "store-db.xml"
        ),
        "pos": (
            base_folder
            / "pos"
        ),
        "itonas": (
            base_folder
            / "itonas"
        ),
        "production": (
            base_folder
            / "production"
        ),
        "way": (
            base_folder
            / "way"
        ),
        "validation": (
            base_folder
            / "validation"
        ),
        "reports": (
            base_folder
            / "reports"
        )
    }


def prepare_output_folder(
    base_folder=DEFAULT_OUTPUT_FOLDER
):
    paths = build_output_paths(
        base_folder
    )

    paths["root"].mkdir(
        exist_ok=True
    )

    paths["pos"].mkdir(
        parents=True,
        exist_ok=True
    )

    paths["itonas"].mkdir(
        parents=True,
        exist_ok=True
    )

    paths["production"].mkdir(
        parents=True,
        exist_ok=True
    )

    paths["way"].mkdir(
        parents=True,
        exist_ok=True
    )

    paths["validation"].mkdir(
        parents=True,
        exist_ok=True
    )

    paths["reports"].mkdir(
        parents=True,
        exist_ok=True
    )

    return paths


def clean_previous_output(
    base_folder=DEFAULT_OUTPUT_FOLDER
):
    base_folder = Path(
        base_folder
    )

    if base_folder.exists():

        shutil.rmtree(
            base_folder
        )

    return prepare_output_folder(
        base_folder
    )