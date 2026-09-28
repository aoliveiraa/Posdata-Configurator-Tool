"""Shared XML construction utilities for the native PosData Builder.

Sprint 2.0.2

All FROM_SCRATCH generators should use this module to create and save XML
artifacts. This module does not copy templates and does not contain
market-specific business rules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple, Union

from lxml import etree


XML_ENCODING = "UTF-8"

XmlNode = Union[etree._Element, etree._ElementTree]


class XmlFactory:
    """Factory and helper methods for XML documents created from scratch."""

    @staticmethod
    def _root(node: XmlNode) -> etree._Element:
        """Return the root element from an Element or ElementTree."""
        if isinstance(node, etree._ElementTree):
            root = node.getroot()
        elif isinstance(node, etree._Element):
            root = node
        else:
            raise TypeError(
                "XML node must be an lxml.etree._Element "
                "or lxml.etree._ElementTree."
            )

        if root is None:
            raise ValueError("XML document has no root element.")

        return root

    @staticmethod
    def _attributes(
        attributes: Optional[Mapping[str, Any]],
    ) -> Dict[str, str]:
        """Normalize attributes and omit values explicitly set to None."""
        if not attributes:
            return {}

        return {
            str(key): str(value)
            for key, value in attributes.items()
            if value is not None
        }

    @staticmethod
    def create_posdb_document() -> etree._Element:
        """Create a new PosDB root element."""
        return etree.Element("PosDB")

    @staticmethod
    def create_posdb_tree() -> etree._ElementTree:
        """Create a new PosDB ElementTree."""
        return etree.ElementTree(XmlFactory.create_posdb_document())

    @staticmethod
    def create_storedb_document() -> Tuple[etree._Element, etree._Element]:
        """Create Document -> StoreDB and return both elements."""
        document = etree.Element("Document")
        storedb = etree.SubElement(document, "StoreDB")
        return document, storedb

    @staticmethod
    def create_storedb_tree() -> Tuple[etree._ElementTree, etree._Element]:
        """Create a StoreDB ElementTree and return the tree and StoreDB node."""
        document, storedb = XmlFactory.create_storedb_document()
        return etree.ElementTree(document), storedb

    @staticmethod
    def add_element(
        parent: etree._Element,
        tag: str,
        attributes: Optional[Mapping[str, Any]] = None,
        text: Optional[Any] = None,
    ) -> etree._Element:
        """Add a child element with optional attributes and text."""
        if not isinstance(parent, etree._Element):
            raise TypeError("Parent must be an lxml.etree._Element.")

        normalized_tag = str(tag or "").strip()
        if not normalized_tag:
            raise ValueError("XML tag cannot be empty.")

        element = etree.SubElement(
            parent,
            normalized_tag,
            attrib=XmlFactory._attributes(attributes),
        )

        if text is not None:
            element.text = str(text)

        return element

    @staticmethod
    def add_configuration(
        parent: etree._Element,
        name: Optional[str] = None,
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> etree._Element:
        """Add a Configuration element.

        The name attribute is optional because some PosData structures use an
        unnamed Configuration container, including StoreDB variants.
        """
        values: Dict[str, Any] = dict(attributes or {})
        if name is not None:
            values["name"] = name
        return XmlFactory.add_element(parent, "Configuration", values)

    @staticmethod
    def add_section(
        parent: etree._Element,
        name: str,
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> etree._Element:
        """Add a named Section element under the supplied parent."""
        values: Dict[str, Any] = dict(attributes or {})
        values["name"] = name
        return XmlFactory.add_element(parent, "Section", values)

    @staticmethod
    def add_parameter(
        parent: etree._Element,
        name: str,
        value: Any,
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> etree._Element:
        """Add a named Parameter element with a value attribute."""
        values: Dict[str, Any] = dict(attributes or {})
        values["name"] = name
        values["value"] = value
        return XmlFactory.add_element(parent, "Parameter", values)

    @staticmethod
    def add_member(
        parent: etree._Element,
        name: str,
        value: Optional[Any] = None,
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> etree._Element:
        """Add a Member element with an optional value."""
        values: Dict[str, Any] = dict(attributes or {})
        values["name"] = name
        if value is not None:
            values["value"] = value
        return XmlFactory.add_element(parent, "Member", values)

    @staticmethod
    def add_used_services(parent: etree._Element) -> etree._Element:
        """Add a UsedServices container."""
        return XmlFactory.add_element(parent, "UsedServices")

    @staticmethod
    def add_services(parent: etree._Element) -> etree._Element:
        """Add a Services container."""
        return XmlFactory.add_element(parent, "Services")

    @staticmethod
    def add_adaptors(parent: etree._Element) -> etree._Element:
        """Add an Adaptors container."""
        return XmlFactory.add_element(parent, "Adaptors")

    @staticmethod
    def add_used_service(
        parent: etree._Element,
        service_name: str,
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> etree._Element:
        """Add a UsedService reference."""
        values: Dict[str, Any] = dict(attributes or {})
        values["name"] = service_name
        return XmlFactory.add_element(parent, "UsedService", values)

    @staticmethod
    def add_service(
        parent: etree._Element,
        name: str,
        service_type: str,
        start_on_load: Optional[bool] = True,
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> etree._Element:
        """Add a Service definition.

        startOnLoad is omitted when start_on_load is None. This allows a native
        generator to reproduce structures where that attribute is not valid.
        """
        values: Dict[str, Any] = dict(attributes or {})
        values["name"] = name
        values["type"] = service_type

        if start_on_load is not None:
            values["startOnLoad"] = "true" if start_on_load else "false"

        return XmlFactory.add_element(parent, "Service", values)

    @staticmethod
    def find_configuration(
        node: XmlNode,
        name: Optional[str] = None,
    ) -> Optional[etree._Element]:
        """Find the first Configuration element, optionally by exact name."""
        root = XmlFactory._root(node)

        if name is None:
            matches = root.xpath(".//Configuration")
        else:
            matches = root.xpath(
                ".//Configuration[@name=$name]",
                name=str(name),
            )

        return matches[0] if matches else None

    @staticmethod
    def find_section(
        node: XmlNode,
        name: str,
    ) -> Optional[etree._Element]:
        """Find the first Section element with the exact supplied name."""
        root = XmlFactory._root(node)
        matches = root.xpath(
            ".//Section[@name=$name]",
            name=str(name),
        )
        return matches[0] if matches else None

    @staticmethod
    def find_child(
        parent: etree._Element,
        tag: str,
    ) -> Optional[etree._Element]:
        """Find the first direct child with the supplied tag."""
        if not isinstance(parent, etree._Element):
            raise TypeError("Parent must be an lxml.etree._Element.")
        return parent.find(str(tag))

    @staticmethod
    def find_or_create_child(
        parent: etree._Element,
        tag: str,
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> etree._Element:
        """Find a direct child or create it under the supplied parent."""
        existing = XmlFactory.find_child(parent, tag)
        if existing is not None:
            return existing
        return XmlFactory.add_element(parent, tag, attributes)

    @staticmethod
    def to_bytes(
        node: XmlNode,
        pretty_print: bool = True,
    ) -> bytes:
        """Serialize an Element or ElementTree as UTF-8 XML bytes."""
        root = XmlFactory._root(node)
        return etree.tostring(
            root,
            pretty_print=pretty_print,
            xml_declaration=True,
            encoding=XML_ENCODING,
        )

    @staticmethod
    def validate_xml(node: XmlNode) -> Dict[str, Any]:
        """Validate that a node can be serialized and parsed as XML."""
        result: Dict[str, Any] = {
            "status": "PASS",
            "root_tag": None,
            "errors": [],
        }

        try:
            root = XmlFactory._root(node)
            result["root_tag"] = str(root.tag)
            etree.fromstring(XmlFactory.to_bytes(root, pretty_print=False))
        except (TypeError, ValueError, etree.LxmlError) as error:
            result["status"] = "FAIL"
            result["errors"].append(str(error))

        return result

    @staticmethod
    def save(
        node: XmlNode,
        output_file: Union[str, Path],
        pretty_print: bool = True,
    ) -> Path:
        """Validate and write XML to disk."""
        validation = XmlFactory.validate_xml(node)
        if validation["status"] != "PASS":
            details = "\n- ".join(validation["errors"])
            raise ValueError(f"Invalid XML:\n- {details}")

        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            XmlFactory.to_bytes(
                node,
                pretty_print=pretty_print,
            )
        )
        return path
