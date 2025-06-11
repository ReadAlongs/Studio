import io
from unittest import main

from basic_test_case import BasicTestCase
from lxml import etree
from packaging.version import Version

from readalongs._version import READALONG_FILE_FORMAT_VERSION
from readalongs.text.util import add_translation_ids, load_xml, migrate_ras, parse_xml


class TestRASMigration(BasicTestCase):
    """Testing RAS XML file migration to latest DTD version."""

    def test_add_translation_ids(self):
        """Test normal translation ids generation."""

        if Version(READALONG_FILE_FORMAT_VERSION) <= Version("1.2.0"):
            self.skipTest(
                "DTD version is still 1.2, add_translation_ids() is never run."
            )

        xml = parse_xml(
            """<p>
            <s id="t0b0d0p0s0" />
            <s do-not-align="true" />
            <s do-not-align="true" />
            <graphic>force siblings scanning to skip non-s elements.</graphic>
            <s id="t0b0d0p0s1" />
            <s do-not-align="true" /></p>"""
        )

        xml = add_translation_ids(xml)
        self.assertEqual(
            [s.get("id") for s in xml.findall(".//s")],
            [
                "t0b0d0p0s0",
                "t0b0d0p0s0tr0",
                "t0b0d0p0s0tr1",
                "t0b0d0p0s1",
                "t0b0d0p0s1tr0",
            ],
            "generated ids are not correct",
        )

        self.assertEqual(
            [s.get("sentence-id") for s in xml.findall(".//s")],
            [None, "t0b0d0p0s0", "t0b0d0p0s0", None, "t0b0d0p0s1"],
            "sentence-ids are not correct",
        )

    def test_add_translation_ids_with_colliding_ids(self):
        """Validate that translation ids are going to be globally unique."""

        if Version(READALONG_FILE_FORMAT_VERSION) <= Version("1.2.0"):
            self.skipTest(
                "DTD version is still 1.2, add_translation_ids() is never run."
            )

        xml = parse_xml(
            """<p>
            <graphic id="t0b0d0p0s0tr0">
                generate an id that will conflict, forcing the algo to generate a unique one.
            </graphic>
            <s id="t0b0d0p0s0" />
            <s do-not-align="true" />
            <s do-not-align="true" /></p>"""
        )

        xml = add_translation_ids(xml)
        self.assertEqual(
            [s.get("id") for s in xml.findall(".//s")],
            ["t0b0d0p0s0", "t0b0d0p0s0tr1", "t0b0d0p0s0tr2"],
            "generated ids are not correct",
        )

    def test_add_translation_ids_with_missing_ids(self):
        """Validate that translation ids are not generated if
        the aligned sentence does not have an id."""
        if Version(READALONG_FILE_FORMAT_VERSION) <= Version("1.2.0"):
            self.skipTest(
                "DTD version is still 1.2, add_translation_ids() is never run."
            )

        xml = parse_xml(
            """<p>
            <s />
            <s do-not-align="true" />
            <s do-not-align="true" /></p>"""
        )

        xml = add_translation_ids(xml)
        self.assertEqual(
            [s.get("id") for s in xml.findall(".//s")],
            [None, None, None],
            "generated ids should not have been generated",
        )

        self.assertEqual(
            [s.get("sentence-id") for s in xml.findall(".//s")],
            [None, None, None],
            "sentence-ids should not have been generated",
        )

    def test_add_translation_ids_does_not_overwrite_existing_ids(self):
        """Validate the method does not overwrite existing id and
        sentence-id attributes."""

        if Version(READALONG_FILE_FORMAT_VERSION) <= Version("1.2.0"):
            self.skipTest(
                "DTD version is still 1.2, add_translation_ids() is never run."
            )

        xml = parse_xml(
            """<p>
        <s id="s0" />
        <s do-not-align="true" id="a-user-id" sentence-id="a-sentence-id" /></p>"""
        )

        xml = add_translation_ids(xml)
        self.assertEqual(
            [s.get("id") for s in xml.findall(".//s")],
            ["s0", "a-user-id"],
            "existing id attribute should not have been overwritten",
        )

        self.assertEqual(
            [s.get("sentence-id") for s in xml.findall(".//s")],
            [None, "a-sentence-id"],
            "sentence-ids should not have been overwritten",
        )

    def test_parse_xml(self):
        """Verify that parse_xml calls migrate_ras() when provided a
        read along xml document."""
        xml = parse_xml(test_ras_document)
        self.assertEqual(xml.get("version"), READALONG_FILE_FORMAT_VERSION)

    def test_load_xml(self):
        """Verify that load_xml calls migrate_ras() when provided a
        read along xml document."""
        xml = load_xml(io.BytesIO(test_ras_document))
        self.assertEqual(xml.get("version"), READALONG_FILE_FORMAT_VERSION)

    def test_migrate_ras_v1_2_1(self):
        """Test migration of DTD version<=1.2 to version 1.2.1 which
        introduces the generation of dna ids and sentence-id."""
        if Version(READALONG_FILE_FORMAT_VERSION) <= Version("1.2.0"):
            self.skipTest("DTD version is still 1.2, migrate_ras() is never run.")

        xml = _test_document()

        migrate_ras(xml, to_version=Version("1.2.1"))
        self.assertEqual(xml.get("version"), "1.2.1")
        self.assertEqual(
            [s.get("id") for s in xml.findall(".//s")],
            [
                "t0b0d0p0s0",
                "t0b0d0p0s0tr0",
                "t0b0d0p0s0tr1",
            ],
            "generated ids are not correct",
        )

        self.assertEqual(
            [s.get("sentence-id") for s in xml.findall(".//s")],
            [None, "t0b0d0p0s0", "t0b0d0p0s0"],
            "sentence-ids are not correct",
        )

    def test_migrate_ras_v1_3_0(self):
        """Example test to demonstrate the to_version argument of migrate_ras()"""
        if Version(READALONG_FILE_FORMAT_VERSION) <= Version("1.2.0"):
            self.skipTest("DTD version is still 1.2, migrate_ras() is never run.")

        xml = _test_document()
        migrate_ras(xml, to_version=Version("1.3.0"))
        self.assertEqual(xml.get("version"), "1.3")


def _test_document() -> etree.Element:
    """Helper method to load the test document without relying
    on parse_xml() or load_xml() functions."""
    return etree.fromstring(
        test_ras_document,
        parser=etree.XMLParser(resolve_entities=False),
    )


# A modified document that has been processed by add_ids()
test_ras_document = bytes(
    """<?xml version='1.0' encoding='utf-8'?>
<read-along version="1.2">
  <meta name="generator" content="@readalongs/studio (cli) 1.2.1" id="meta0"/>

    <text xml:lang="und" fallback-langs="" id="t0">
        <body id="t0b0">
            <div type="page" id="t0b0d0">
              <p id="t0b0d0p0">
                  <s id="t0b0d0p0s0" />
                  <s do-not-align="true" />
                  <s do-not-align="true" />
                </p>
            </div>
        </body>
    </text>
</read-along>
""",
    encoding="utf8",
)

if __name__ == "__main__":
    main()
