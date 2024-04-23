#!/usr/bin/env python

"""Unit test suite for our XML tokenizer module"""

from unittest import TestCase, main

from lxml import etree

from readalongs.text import tokenize_xml
from readalongs.text.util import parse_xml


class TestTokenizer(TestCase):
    """Test the tokenize_xml function"""

    def test_simple(self):
        """Simple tokenization test case"""
        txt = """<document>
<s xml:lang="atj">Kwei! Tan e ici matisihin?</s>
</document>
"""
        ref = """<document>
<s xml:lang="atj"><w>Kwei</w>! <w>Tan</w> <w>e</w> <w>ici</w> <w>matisihin</w>?</s>
</document>"""
        xml = parse_xml(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        # print(etree.tounicode(tokenized))
        self.assertEqual(etree.tounicode(tokenized), ref)

    def test_mixed_lang(self):
        """Tokenization test case with mixed languages"""
        txt = """<document>
<s xml:lang="atj">Kwei! Tan e ici matisihin?</s>
<s xml:lang="fra">Bonjour! Comment ça va?</s>
</document>
"""
        ref = """<document>
<s xml:lang="atj"><w>Kwei</w>! <w>Tan</w> <w>e</w> <w>ici</w> <w>matisihin</w>?</s>
<s xml:lang="fra"><w>Bonjour</w>! <w>Comment</w> <w>ça</w> <w>va</w>?</s>
</document>"""
        xml = parse_xml(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        # print(etree.tounicode(tokenized))
        self.assertEqual(etree.tounicode(tokenized), ref)

    def test_mixed_words(self):
        """Tokenization should be bypassed when <w> elements are already found in the input"""
        txt = """<document>
<s xml:lang="atj">Kwei! (<w xml:lang="fra">Bonjour</w>!)</s>
<s xml:lang="atj">Tan e ici matisihin?</s>
</document>
"""
        ref = """<document>
<s xml:lang="atj">Kwei! (<w xml:lang="fra">Bonjour</w>!)</s>
<s xml:lang="atj">Tan e ici matisihin?</s>
</document>"""
        xml = parse_xml(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        # print(etree.tounicode(tokenized))
        self.assertEqual(etree.tounicode(tokenized), ref)

    def test_comments(self):
        """Make sure tokenize_xml ignores stuff inside comments"""
        txt = """<document>
<s xml:lang="atj">Kwei! (<subsent xml:lang="fra">Bonjour</subsent>!)</s>
<!--<s>comments</s> <w>should</w> <p>be ignored</p>-->
<s xml:lang="atj">Tan e ici matisihin?</s>
</document>
"""
        ref = """<document>
<s xml:lang="atj"><w>Kwei</w>! (<subsent xml:lang="fra"><w>Bonjour</w></subsent>!)</s>
<!--<s>comments</s> <w>should</w> <p>be ignored</p>-->
<s xml:lang="atj"><w>Tan</w> <w>e</w> <w>ici</w> <w>matisihin</w>?</s>
</document>"""
        xml = parse_xml(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        # print(etree.tounicode(tokenized))
        self.assertEqual(etree.tounicode(tokenized), ref)


if __name__ == "__main__":
    main()
