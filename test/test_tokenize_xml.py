from unittest import TestCase, main
from lxml import etree

from readalongs.text import tokenize_xml


class TestTokenizer(TestCase):
    def test_simple(self):
        txt = """<document>
<s xml:lang="atj">Kwei! Tan e ici matisihin?</s>
</document>
"""
        xml = etree.fromstring(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        print(etree.tounicode(tokenized))

    def test_mixed_lang(self):
        txt = """<document>
<s xml:lang="atj">Kwei! Tan e ici matisihin?</s>
<s xml:lang="fra">Bonjour! Comment ça va?</s>
</document>
"""
        xml = etree.fromstring(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        print(etree.tounicode(tokenized))

    def test_mixed_words(self):
        txt = """<document>
<s xml:lang="atj">Kwei! (<w xml:lang="fra">Bonjour</w>!)</s>
<s xml:lang="atj">Tan e ici matisihin?</s>
</document>
"""
        xml = etree.fromstring(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        print(etree.tounicode(tokenized))

    def test_comments(self):
        txt = """<document>
<s xml:lang="atj">Kwei! (<w xml:lang="fra">Bonjour</w>!)</s>
<s xml:lang="atj">Tan e ici matisihin?</s>
</document>
"""
        xml = etree.fromstring(txt)
        tokenized = tokenize_xml.tokenize_xml(xml)
        print(etree.tounicode(tokenized))


if __name__ == "__main__":
    main()
