# Text processing for readalongs

This collection of modules allows structure-aware text-processing for XML documents that are potentially linguistically complex (e.g. have subword units, have multiple languages indicated by xml:lang attributes, etc.).

It produces a pronouncing dictionary containing the pronunciation of each XML element with an "id" attribute, of a particular level of analysis (e.g. word, morpheme, syllable, etc.).  If word elements (tagged as <w>, according to TEI standards) and "id" attributes are not present, they are automatically added.
