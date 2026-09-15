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

from src.transformers.foe_transformer import (
    generate_all_foe,
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

    runtime.generated_foe = (
        generate_all_foe(
            new_posdata_folder=
                runtime.new_posdata_folder,

            output_folder=
                "output/foe",
        )
    )

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

    store_db_result = prepare_store_db(
        new_posdata_folder=(
            runtime.new_posdata_folder
        ),
        output_folder="output"
    )

    runtime.store_db_generation = (
        store_db_result
    )

    store_db_config_result = (
        update_storedb_runtime_configuration(
            store_db_path="output/store-db.xml",
            output_path="output/store-db.xml",
           lab=(
                "RENEIGH"
                if "reneigh"
                in str(runtime.config_path).lower()
                else "RIO"
            )
        )
    )

    runtime.store_db_configuration = (
        store_db_config_result
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

    return runtime