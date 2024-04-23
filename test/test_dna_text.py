#!/usr/bin/env python

"""Test handling of DNA text in tokenization"""

from unittest import main

from basic_test_case import BasicTestCase
from lxml import etree

from readalongs.text import tokenize_xml
from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.util import parse_xml


class TestDNAText(BasicTestCase):
    """Test handling of DNA text in tokenization"""

    def test_tok_all_words(self):
        """By default, all words should get tokenized"""

        txt = """<document xml:lang="fra">
<s>Bonjour! Comment ça va?</s>
<s>Voici une deuxième phrase.</s>
</document>"""
        xml = parse_xml(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        as_txt = etree.tounicode(tokenized)
        # print(etree.tounicode(tokenized))

        ref = """<document xml:lang="fra">
<s><w>Bonjour</w>! <w>Comment</w> <w>ça</w> <w>va</w>?</s>
<s><w>Voici</w> <w>une</w> <w>deuxième</w> <w>phrase</w>.</s>
</document>"""
        # print('as_txt="' + as_txt +'"')
        # print('ref="' + ref +'"')
        self.assertEqual(as_txt, ref)

        with_ids = add_ids(tokenized)
        ids_as_txt = etree.tounicode(with_ids)
        # print('with ids="' + ids_as_txt + '"')
        ref_with_ids = """<document xml:lang="fra">
<s id="s0"><w id="s0w0">Bonjour</w>! <w id="s0w1">Comment</w> <w id="s0w2">ça</w> <w id="s0w3">va</w>?</s>
<s id="s1"><w id="s1w0">Voici</w> <w id="s1w1">une</w> <w id="s1w2">deuxième</w> <w id="s1w3">phrase</w>.</s>
</document>"""
        self.assertEqual(ids_as_txt, ref_with_ids)

    def test_tok_some_words(self):
        """do-not-align text is excluded from tokenization"""

        txt = """<document xml:lang="fra">
<p><s>Bonjour! Comment ça va?</s></p>
<p do-not-align="true"><s>Bonjour! Comment ça va?</s></p>
<s do-not-align="TRUE">Voici une deuxième phrase.</s>
<s>Un <foo do-not-align="1">mot ou deux</foo> à exclure.</s>
</document>"""
        xml = parse_xml(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        as_txt = etree.tounicode(tokenized)
        # print('as_txt="' + as_txt +'"')

        ref = """<document xml:lang="fra">
<p><s><w>Bonjour</w>! <w>Comment</w> <w>ça</w> <w>va</w>?</s></p>
<p do-not-align="true"><s>Bonjour! Comment ça va?</s></p>
<s do-not-align="TRUE">Voici une deuxième phrase.</s>
<s><w>Un</w> <foo do-not-align="1">mot ou deux</foo> <w>à</w> <w>exclure</w>.</s>
</document>"""
        self.assertEqual(as_txt, ref)

        with_ids = add_ids(tokenized)
        ids_as_txt = etree.tounicode(with_ids)
        # print('with ids="' + ids_as_txt + '"')
        ref_with_ids = """<document xml:lang="fra">
<p id="p0"><s id="p0s0"><w id="p0s0w0">Bonjour</w>! <w id="p0s0w1">Comment</w> <w id="p0s0w2">ça</w> <w id="p0s0w3">va</w>?</s></p>
<p do-not-align="true"><s>Bonjour! Comment ça va?</s></p>
<s do-not-align="TRUE">Voici une deuxième phrase.</s>
<s id="s0"><w id="s0w0">Un</w> <foo do-not-align="1">mot ou deux</foo> <w id="s0w1">à</w> <w id="s0w2">exclure</w>.</s>
</document>"""
        self.assertEqual(ids_as_txt, ref_with_ids)

    def test_tok_div_p_s(self):
        """Text inside a DNA div, p or s does not get tokenized"""

        txt = """<document xml:lang="fra">
<div>
<p> <s>Une phrase.</s> </p>
<p> <s>Deux phrases.</s> </p>
</div>
<div do-not-align="TRUE">
<p> <s>Une phrase.</s> </p>
<p> <s>Deux phrases.</s> </p>
</div>
<div>
<p do-not-align="1"> <s>Une phrase.</s> </p>
<p> <s do-not-align="true">Deux phrases.</s> </p>
<p> <s>Trois phrases.</s> </p>
</div>
</document>"""
        xml = parse_xml(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        as_txt = etree.tounicode(tokenized)
        # print('as_txt="' + as_txt +'"')

        ref = """<document xml:lang="fra">
<div>
<p> <s><w>Une</w> <w>phrase</w>.</s> </p>
<p> <s><w>Deux</w> <w>phrases</w>.</s> </p>
</div>
<div do-not-align="TRUE">
<p> <s>Une phrase.</s> </p>
<p> <s>Deux phrases.</s> </p>
</div>
<div>
<p do-not-align="1"> <s>Une phrase.</s> </p>
<p> <s do-not-align="true">Deux phrases.</s> </p>
<p> <s><w>Trois</w> <w>phrases</w>.</s> </p>
</div>
</document>"""
        self.assertEqual(as_txt, ref)

        with_ids = add_ids(tokenized)
        ids_as_txt = etree.tounicode(with_ids)
        # print('with ids="' + ids_as_txt + '"')

        ref_with_ids = """<document xml:lang="fra">
<div id="d0">
<p id="d0p0"> <s id="d0p0s0"><w id="d0p0s0w0">Une</w> <w id="d0p0s0w1">phrase</w>.</s> </p>
<p id="d0p1"> <s id="d0p1s0"><w id="d0p1s0w0">Deux</w> <w id="d0p1s0w1">phrases</w>.</s> </p>
</div>
<div do-not-align="TRUE">
<p> <s>Une phrase.</s> </p>
<p> <s>Deux phrases.</s> </p>
</div>
<div id="d1">
<p do-not-align="1"> <s>Une phrase.</s> </p>
<p id="d1p0"> <s do-not-align="true">Deux phrases.</s> </p>
<p id="d1p1"> <s id="d1p1s0"><w id="d1p1s0w0">Trois</w> <w id="d1p1s0w1">phrases</w>.</s> </p>
</div>
</document>"""
        self.assertEqual(ids_as_txt, ref_with_ids)

    def test_dna_word(self):
        """You can't have a DNA <w> element, that's reserved for tokens to align"""

        txt = """<s xml:lang="fra">Une <w do-not-align="true">exclude</w> phrase.</s>"""
        xml = parse_xml(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        self.assertRaises(RuntimeError, add_ids, tokenized)

    def test_dna_word_nested(self):
        """You also can't have a <w> element inside a DNA element"""

        txt = """<s xml:lang="fra">Une <foo do-not-align="true"><bar><w>exclude</w></bar></foo> phrase.</s>"""
        xml = parse_xml(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        self.assertRaises(RuntimeError, add_ids, tokenized)


if __name__ == "__main__":
    main()
