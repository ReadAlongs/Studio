# readlongs
Audiobook alignment for North American indigenous languages

# end product

The concept is a web application with a series of stages of
processing, which ultimately leads to a time-aligned audiobook -
i.e. a package of:

- SMIL file describing time alignments
- TEI file describing text
- Audio file (WAV or MP3)

Which can be loaded using the read-along JavaScript component.

Optionally a book can be generated as a standalone HTML page or
(maybe) as an ePub file.

1. (optional) Pre-segment inputs, consisting of:
   - Single audio file
   - Text with page markings (assume paragraph breaks = pages)
2. Input pages: each page consists of
   - Image file
   - Audio file
   - Text
3. Run alignment
4. View output and download components

# roadmap

- MVP app:
  - Single page (image, audio, text)
  - Select language (crl or atj for now)
  - Run alignment and launch read-along app with output
