from src.utils.xml_loader import load_xml


def analyze_storedb(store_db_path):

    tree = load_xml(store_db_path)

    store_id = tree.xpath("//StoreId/text()")
    city = tree.xpath("//City/text()")
    country = tree.xpath("//Country/text()")

    main_screen = tree.xpath(
        "//Parameter[@name='mainScreenNumber']/@value"
    )

    business_limits = tree.xpath(
        "//BusinessLimits"
    )

    return {
        "store_id": store_id[0] if store_id else "UNKNOWN",
        "city": city[0] if city else "UNKNOWN",
        "country": country[0] if country else "UNKNOWN",
        "main_screen":
            main_screen[0] if main_screen else "NOT FOUND",
        "business_limits":
            len(business_limits) > 0
    }