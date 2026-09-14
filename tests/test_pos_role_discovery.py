import tempfile
from pathlib import Path
import unittest

from src.discovery.pos_role_discovery import (
    discover_pos_role,
    normalize_pos_role,
)

POS_SERVICE_TEMPLATE = """\
<PosDB>
  <Services>
    <Service name="0001" type="POS">
      <Configuration imports="POS">
        <Section name="PosType">
          <Parameter name="{parameter}" value="{value}" />
        </Section>
      </Configuration>
    </Service>
  </Services>
</PosDB>
"""


class UniversalPosRoleDiscoveryTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize_pos_role("FRONT_COUNTER"), "FC")
        self.assertEqual(normalize_pos_role("drive thru"), "DT")
        self.assertEqual(normalize_pos_role("DRIVE-THROUGH"), "DT")
        self.assertIsNone(normalize_pos_role("CSO"))

    def test_pod_front_counter(self):
        result = discover_pos_role(
            self._write(POS_SERVICE_TEMPLATE.format(parameter="POD", value="FRONT_COUNTER"))
        )
        self.assertEqual(result["role"], "FC")
        self.assertEqual(result["role_source"], "xml_pos_service_pod")
        self.assertEqual(result["status"], "READY")

    def test_pod_drive_thru(self):
        result = discover_pos_role(
            self._write(POS_SERVICE_TEMPLATE.format(parameter="POD", value="DRIVE_THRU"))
        )
        self.assertEqual(result["role"], "DT")

    def test_rempod_fallback(self):
        result = discover_pos_role(
            self._write(POS_SERVICE_TEMPLATE.format(parameter="RemPOD", value="FRONT_COUNTER"))
        )
        self.assertEqual(result["role"], "FC")
        self.assertEqual(result["role_source"], "xml_pos_service_rempod")

    def test_filename_fallback(self):
        result = discover_pos_role(self._write("<PosDB />"), filename="_POS01_DT_pos-db.xml")
        self.assertEqual(result["role"], "DT")
        self.assertEqual(result["confidence"], "MEDIUM")

    def test_numbered_filename_is_not_role(self):
        result = discover_pos_role(self._write("<PosDB />"), filename="_POS0001_pos-db.xml")
        self.assertIsNone(result["role"])
        self.assertEqual(result["status"], "REVIEW REQUIRED")

    def test_generic_cod_podtype_does_not_create_false_positive(self):
        xml = """
        <PosDB>
          <Service name="0002" type="COD">
            <Adaptor name="npAdpCodUI">
              <Section name="NGCODUnitSetting">
                <Parameter name="PODType" value="DT" />
              </Section>
            </Adaptor>
          </Service>
        </PosDB>
        """
        result = discover_pos_role(self._write(xml), filename="_POS0001_pos-db.xml")
        self.assertIsNone(result["role"])

    def test_invalid_xml_requires_review(self):
        result = discover_pos_role(self._write("<PosDB>"))
        self.assertEqual(result["status"], "REVIEW REQUIRED")
        self.assertTrue(result["warnings"])

    def _write(self, content):
        directory = tempfile.mkdtemp()
        path = Path(directory) / "candidate.xml"
        path.write_text(content, encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main(verbosity=2)
