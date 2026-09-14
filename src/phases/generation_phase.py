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

    runtime.generated_store_cod = (
        generate_store_cod_file(
            cod_target=
                runtime.cod_target,

            store_file=
                "output/store-db.xml",
        )
    )

    return runtime