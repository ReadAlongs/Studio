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
as an ePub file.

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

# running the web app

1. `pip install -e .`
2. `python`
3. `>>> from readalongs.app import app`
4. `app.run()`

# generating an ePub

1. `pip install -e .`
2. `readalongs_align --output-xhtml XMLFILE WAVFILE OUTPUTNAME`
3. `readalongs_create_epub OUTPUTNAME.smil OUTPUTNAME.epub`

# Docker

To build the Docker container, run:

    docker build . --tag=readlong-studio

To run the Flask web app from the Docker container:

    docker run -p 5000:5000 -it readalong-studio

Then you should be able to visit http://localhost:5000/.
