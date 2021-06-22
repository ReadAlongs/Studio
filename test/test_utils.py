#!/usr/bin/env python3

from unittest import TestCase, main

from lxml import etree

from readalongs.text.util import iterate_over_text


class TestTextUtils(TestCase):
    def test_iterate_over_text(self):
        txt = (
            '<text><s><w xml:lang="eng">word</w>,<w>word2</w>;</s>'
            + '<s xml:lang="und">blah blah</s></text>'
        )
        xml = etree.fromstring(txt)
        self.assertEqual(
            list(iterate_over_text(xml)),
            [
                ("eng", "word"),
                (None, ","),
                (None, "word2"),
                (None, ";"),
                ("und", "blah blah"),
            ],
        )

    def test_iterate_over_text2(self):
        # Patrickxtła̱n means my name is Patrick, in Kwak'wala
        txt = (
            '<xml><s><w xml:lang="eng">Patrick</w><w xml:lang="kwk">xtła̱n</w></s>'
            + '<s><w xml:lang="und">Patrickxtła̱n</w></s></xml>'
        )
        xml = etree.fromstring(txt)
        self.assertEqual(
            list(iterate_over_text(xml)),
            [("eng", "Patrick"), ("kwk", "xtła̱n"), ("und", "Patrickxtła̱n")],
        )


if __name__ == "__main__":
    main()
