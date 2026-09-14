from lxml import etree

from src.utils.xml_loader import (
    load_xml,
    save_xml
)


def update_main_screen(
        store_db_path,
        output_path,
        new_screen):

    tree = load_xml(store_db_path)

    nodes = tree.xpath(
        "//Parameter[@name='mainScreenNumber']"
    )

    if nodes:

        nodes[0].set(
            "value",
            str(new_screen)
        )

    save_xml(
        tree,
        output_path
    )

    return True


def update_business_limits(
        store_db_path,
        output_path,
        business_limits_file):

    tree = load_xml(store_db_path)

    business_tree = etree.parse(
        business_limits_file
    )

    new_limits = business_tree.getroot()

    old_limits = tree.xpath(
        "//BusinessLimits"
    )

    if old_limits:

        parent = old_limits[0].getparent()

        parent.replace(
            old_limits[0],
            new_limits
        )

    save_xml(
        tree,
        output_path
    )