from src.utils.xml_loader import load_xml


def analyze_screens(screen_path):

    tree = load_xml(screen_path)

    screens = []

    for screen in tree.xpath("//Screen"):

        number = screen.get("number")
        title = screen.get("title")

        if title:

            screens.append({
                "number": number,
                "title": title
            })

    return screens


def find_lunch_screen(screens):

    for screen in screens:

        title = screen["title"].lower()

        if "lunch" in title:

            return screen

    return None