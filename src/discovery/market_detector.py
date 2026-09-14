from src.utils.xml_loader import load_xml


def detect_market(store_db_path):

    tree = load_xml(store_db_path)

    country = tree.xpath("//Country/text()")

    return {
        "country": country[0] if country else "UNKNOWN"
    }