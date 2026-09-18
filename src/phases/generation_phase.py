from pathlib import Path
import shutil

from src.runtime_context import (
    RuntimeContext,
)

from src.transformers.pos_transformer import (
    generate_all_pos,
)

from src.transformers.xmlrpccli_transformer import (
    generate_xmlrpccli_configuration,
)

from src.transformers.way_transformer import (
    generate_way_file,
)

from src.transformers.production_transformer import (
    generate_all_production,
)


from src.transformers.kvs_transformer import (
    generate_all_itonas,
)

from src.transformers.cod_transformer import (
    generate_cod_file,
    generate_store_cod_file,
)

from src.transformers.storedb_transformer import (
    update_storedb_runtime_configuration,
)

from src.transformers.store_db_operation_mode_transformer import (
    StoreDbOperationModeTransformer,
)

from src.transformers.cashdrawer_transformer import (
    CashDrawerTransformer,
)

def prepare_store_db(
    new_posdata_folder,
    output_folder
):
    """
    Copies the StoreDB from the new PosData
    to the generation output folder.

    The copied file becomes the working StoreDB
    used by XMLRPCCLI, COD and Store COD generation.
    """

    result = {
        "prepared": False,
        "source_file": None,
        "output_file": None,
        "changes": [],
        "warnings": [],
        "errors": [],
    }

    if new_posdata_folder is None:
        result["errors"].append(
            "New PosData folder was not provided "
            "for StoreDB preparation."
        )

        return result

    if output_folder is None:
        result["errors"].append(
            "Output folder was not provided "
            "for StoreDB preparation."
        )

        return result

    new_posdata_folder = Path(
        new_posdata_folder
    )

    output_folder = Path(
        output_folder
    )

    source_file = (
        new_posdata_folder
        / "store-db.xml"
    )

    output_file = (
        output_folder
        / "store-db.xml"
    )

    result["source_file"] = source_file
    result["output_file"] = output_file

    if not source_file.exists():
        result["errors"].append(
            "StoreDB source file was not found: "
            f"{source_file}"
        )

        return result

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    try:
        shutil.copy2(
            source_file,
            output_file
        )

    except Exception as error:
        result["errors"].append(
            "Unable to copy StoreDB to output: "
            f"{error}"
        )

        return result

    if not output_file.exists():
        result["errors"].append(
            "StoreDB copy was completed, but the "
            "output file could not be found: "
            f"{output_file}"
        )

        return result

    result["prepared"] = True

    result["changes"].append(
        "StoreDB copied to generation output."
    )

    return result


def run_generation_phase(
    runtime: RuntimeContext,
) -> RuntimeContext:


    store_db_result = prepare_store_db(
        new_posdata_folder=(
            runtime.new_posdata_folder
        ),
        output_folder="output"
    )

    runtime.store_db_generation = (
        store_db_result
    )



    #
    # POS
    #

    runtime.generated_pos = (
        generate_all_pos(
            pos_mapping=
                runtime.pos_mapping,

            pos_machine_lookup=
                runtime.runtime_pos_machine_lookup,

            new_posdata_folder=
                runtime.new_posdata_folder,

            output_folder=
                "output/pos",
        )
    )

    #
    # XMLRPCCLI
    #

    runtime.xmlrpccli_result = (
        generate_xmlrpccli_configuration(
            config_path=
                runtime.config_path,

            current_pos_folder=
                runtime.current_posdata_folder,

            output_pos_folder=
                "output/pos",

            current_store_file=
                f"{runtime.current_posdata_folder}/store-db.xml",

            output_store_file=
                "output/store-db.xml",

            allowed_pos_nodes=
                runtime.generated_pos,
        )
    )

    #
    # WAY
    #

    runtime.generated_way = (
        generate_way_file(
            new_posdata_folder=
                runtime.new_posdata_folder,

            output_folder=
                "output/way",

            config_path=
                runtime.config_path,
        )
    )

    #
    # PRODUCTION
    #

    runtime.generated_production = (
        generate_all_production(
            new_posdata_folder=
                runtime.new_posdata_folder,

            output_folder=
                "output/production",
        )
    )

    #
    # FOE
    #
    # FOE is embedded in the generated WAYSTATION file.
    # No separate FOE file must be exported.
    #

    way_generated = (
        runtime.generated_way.get(
            "generated",
            False
        )
    )

    runtime.generated_foe = [
        {
            "generated": way_generated,
            "file": (
                runtime.generated_way.get(
                    "output_file"
                )
            ),
            "output_file": (
                runtime.generated_way.get(
                    "output_file"
                )
            ),
            "changes": [
                (
                    "FOE configuration validated "
                    "inside WAYSTATION output."
                )
            ] if way_generated else [],
            "warnings": (
                runtime.generated_way.get(
                    "warnings",
                    []
                )
            ),
            "errors": (
                runtime.generated_way.get(
                    "errors",
                    []
                )
            ),
        }
    ]

    #
    # ITONAS
    #

    runtime.generated_itonas = (
        generate_all_itonas(
            kvs_mapping=
                runtime.kvs_mapping,

            new_posdata_folder=
                runtime.new_posdata_folder,

            output_folder=
                "output/itonas",

            reference_posdata_folder=
                runtime.current_posdata_folder,
        )
    )

    #
    # COD
    #

    runtime.generated_cod = (
        generate_cod_file(
            cod_target=
                runtime.cod_target,

            config_path=
                runtime.config_path,

            output_folder=
                "output/pos",
        )
    )

    #
    # STORE COD
    #

    store_db_config_result = (
        update_storedb_runtime_configuration(
            store_db_path="output/store-db.xml",
            output_path="output/store-db.xml",
            lab=runtime.selected_lab,
        )
    )

    runtime.store_db_configuration = (
        store_db_config_result
    )

    #
    # STOREDB OPERATION MODE
    #
    operation_mode_transformer = (
        StoreDbOperationModeTransformer()
    )

    operation_mode_result = (
        operation_mode_transformer.transform_file(
            source_file="output/store-db.xml",
            output_file="output/store-db.xml",
        )
    )

    import pathlib

    xml_text = pathlib.Path(
        "output/store-db.xml"
    ).read_text(
        encoding="utf-8"
    )



    runtime.store_db_operation_mode = (
        operation_mode_result
    )

    print()
    print("OPERATION MODE")
    print("-" * 50)

    print(
        f"Modified: {operation_mode_result.modified}"
    )

    print(
        f"Configuration Found: "
        f"{operation_mode_result.configuration_found}"
    )

    print(
        f"Section Created: "
        f"{operation_mode_result.section_created}"
    )

    print(
        f"Parameters Created: "
        f"{operation_mode_result.parameters_created}"
    )

    print(
        f"Parameters Updated: "
        f"{operation_mode_result.parameters_updated}"
    )

    print(
        f"Duplicates Removed: "
        f"{operation_mode_result.duplicates_removed}"
    )

    #
    # CASH DRAWER
    #
    cash_drawer_transformer = (
        CashDrawerTransformer()
    )

    cash_drawer_result = (
        cash_drawer_transformer.transform_file(
            source_file="output/store-db.xml",
            output_file="output/store-db.xml",
        )
    )

    runtime.cash_drawer_configuration = (
        cash_drawer_result
    )

    print()
    print("CASH DRAWER")
    print("-" * 50)

    print(
        "Status:",
        (
            "UPDATED"
            if cash_drawer_result.modified
            else "ALREADY DISABLED"
        )
    )

    print(
        "Adaptors Found:",
        cash_drawer_result.adaptors_found,
    )

    print(
        "Adaptors Modified:",
        len(
            cash_drawer_result.adaptors_modified
        ),
    )

    for adaptor_type in (
        cash_drawer_result.adaptors_modified
    ):
        print(
            f"  - {adaptor_type}"
        )

    for warning in cash_drawer_result.warnings:
        print(
            f"WARNING: {warning}"
        )

    print()
    print("STOREDB PREPARATION")
    print("-" * 50)

    print(
        "Source:",
        store_db_result.get(
            "source_file"
        )
    )

    print(
        "Output:",
        store_db_result.get(
            "output_file"
        )
    )

    print(
        "Status:",
        (
            "READY"
            if store_db_result.get(
                "prepared"
            )
            else "FAIL"
        )
    )

    for error in store_db_result.get(
        "errors",
        []
    ):
        print(
            "ERROR:",
            error
        )
    runtime.generated_store_cod = (
        generate_store_cod_file(
            cod_target=
                runtime.cod_target,

            store_file=
                "output/store-db.xml",
        )
    )

    xml_text = pathlib.Path(
        "output/store-db.xml"
    ).read_text(
        encoding="utf-8"
    )

    return runtime