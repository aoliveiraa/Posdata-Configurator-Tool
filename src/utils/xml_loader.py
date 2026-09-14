from lxml import etree


def load_xml(path):
    try:
        return etree.parse(str(path))
    except Exception as e:
        print(f"\nErro ao carregar XML:")
        print(path)
        print(e)
        raise


def save_xml(tree, output_path):
    tree.write(
        str(output_path),
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8"
    )