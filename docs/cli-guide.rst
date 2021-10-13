.. _cli-guide:

Command line interface (CLI) user guide
=======================================

This page contains guidelines on using the ReadAlongs CLI. See also
:ref:`cli-ref` for the full CLI reference.

The ReadAlongs CLI has two main commands: ``readalongs prepare`` and
``readalongs align``.

- If your data is a plain text file, you can run ``prepare`` to turn it into
  XML, which you can then align with ``align``. Doing this in two steps allows
  you to modify the XML file before aligning it (e.g., to mark that some text is
  in a different language, to flag some do-not-align text, or to drop anchors
  in).

- Alternatively, if your plain text file does not need to be modified, you can
  run ``align`` directly and use the ``-i`` option to indicate that the input
  is plain text and not xml. You'll also need the ``-l <language>`` option to
  indicate what language your text is in.

Two additional commands are sometimes useful: ``readalongs tokenize`` and
``readalongs g2p``.

- ``tokenize`` takes the output of ``prepare`` and tokenizes it, wrapping each
  word in the text in a ``<w>`` element.

- ``g2p`` takes the output of ``tokenize`` and mapping each word to its
  phonetic transcription using the g2p library. The phonetic transcription is
  represented using the ARPABET phonetic codes and are added in the ``ARPABET``
  attribute to each ``<w>`` element.

The result of ``tokenize`` or ``g2p`` can be fixed manually if necessary and
then used as input to ``align``.

Getting from TXT to XML with readalongs prepare
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run :ref:`cli-prepare` to prepare an XML file for ``align`` from a TXT file.

``readalongs prepare [options] [story.txt] [story.xml]``

``[story.txt]``: path to the plain text input file (TXT)

``[story.xml]``: Path to the XML output file

The plain text file must be plain text encoded in ``UTF-8`` with one
sentence per line. Paragraph breaks are marked by a blank line, and page
breaks are marked by two blank lines.

+-----------------------------------+-----------------------------------+
| Key Options                       | Option descriptions               |
+===================================+===================================+
| ``-l, --language`` (required)     | The language code for story.txt.  |
+-----------------------------------+-----------------------------------+
| ``-f, --force-overwrite``         | Force overwrite output files      |
|                                   | (handy if you’re troubleshooting  |
|                                   | and will be aligning repeatedly)  |
+-----------------------------------+-----------------------------------+
| ``-h, --help``                    | Displays CLI guide for            |
|                                   | ``prepare``                       |
+-----------------------------------+-----------------------------------+

The ``-l, --language`` argument requires a language’s 3 character `ISO
code <https://en.wikipedia.org/wiki/ISO_639-3>`__ as an argument.

The languages supported by RAS can be listed by running ``readalongs prepare -h``
and they can also be found in the :ref:`cli-prepare` reference.

So, a full command for a story in Algonquin would be something like:

``readalongs prepare -l alq Studio/story.txt Studio/story.xml``

The generated XML will be parsed in to sentences. At this stage you can
edit the XML to have any modifications, such as adding ``do-not-align``
as an attribute of any element in your XML.

.. _dna:

Handling mismatches: do-not-align
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are two types of "do-not-align" (DNA) content: DNA audio and DNA text.

To use DNA text, add ``do-not-align`` as an attribute to any
element in the xml (word, sentence, paragraph, or page).

::

   <w do-not-align="true" id="t0b0d0p0s0w0">dog</w>

If you have already run ``readalongs prepare``, there will be
documentation for DNA text in comments at the beginning of the generated
xml file.

::

   <!-- To exclude any element from alignment, add the do-not-align="true" attribute to
        it, e.g., <p do-not-align="true">...</p>, or
        <s>Some text <foo do-not-align="true">do not align this</foo> more text</s> -->

To use DNA audio, you can specify a frame of time in milliseconds in the
``config.json`` file which you want the aligner to ignore.

::

   "do-not-align":
       {
       "method": "remove",
       "segments":
       [
           {
               "begin": 1,
               "end": 17000
           }
       ]
       }

Use cases for DNA
'''''''''''''''''

-  Spoken introduction in the audio file that has no accompanying text
   (DNA audio)
-  Text that has no matching audio, such as credits/acknowledgments (DNA
   text)

Aligning your text and audio with readalongs align
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run :ref:`cli-align` to align a text file (XML or TXT) and an audio file to
create a time-aligned audiobook.

``readalongs align [options] [story.txt/xml] [story.mp3/wav] [output_base]``

``[story.txt/xml]``: path to the text file (TXT or XML)

``[story.mp3/wav]``: path to the audio file (MP3, WAV or any format
supported by ffmpeg)

``[output_base]``: path to the directory where the output files will be
created, as ``output_base*``

+-----------------------------------+---------------------------------------+
| Key Options                       | Option descriptions                   |
+===================================+=======================================+
| ``-l, --language``                | The language code for story.txt.      |
|                                   | (required if input is plain text)     |
+-----------------------------------+---------------------------------------+
| ``-c, --config PATH``             | Use ReadAlong-Studio                  |
|                                   | configuration file (in JSON           |
|                                   | format)                               |
+-----------------------------------+---------------------------------------+
| ``-i, --text-input``              | Input is plain text (TXT)             |
|                                   | (otherwise it’s assumed to be         |
|                                   | XML)                                  |
+-----------------------------------+---------------------------------------+
| ``--g2p-fallback G2P_FALLBACK``   | Colon-separated list of fallback langs|
|                                   | for g2p; enables the g2p cascade      |
+-----------------------------------+---------------------------------------+
| ``--g2p-verbose``                 | Display verbose g2p error messages    |
+-----------------------------------+---------------------------------------+
| ``-s, --save-temps``              | Save intermediate stages of           |
|                                   | processing and temporary files        |
|                                   | (dictionary, FSG, tokenization,       |
|                                   | etc.)                                 |
+-----------------------------------+---------------------------------------+
| ``-f, --force-overwrite``         | Force overwrite output files          |
|                                   | (handy if you’re troubleshooting      |
|                                   | and will be aligning repeatedly)      |
+-----------------------------------+---------------------------------------+
| ``-h, --help``                    | Displays CLI guide for ``align``      |
+-----------------------------------+---------------------------------------+

See above for more information on the ``-l, --language`` argument.

A full command would be something like:

``readalongs align -f -c Studio/config.json Studio/story.xml Studio/story.mp3 Studio/story/aligned``

The config.json file
~~~~~~~~~~~~~~~~~~~~

Some additional parameters can be specified via a config file: create a JSON
file called ``config.json``, possibly in the same folder as your other ReadAlong
input files for convenience. The config file currently accepts two components:
adding images to your ReadAlongs, and DNA audio (see :ref:`dna`).

To add images, indicate the page number as the key, and the name of the image
file as the value, as an entry in the ``"images"`` dictionary.

::

   { "images": { "0": "p1.jpg", "1": "p2.jpg" } }

Both images and DNA audio can be specified in the same config file, such
as in the example below:

::

   {
       "images":
           {
               "0": "image-for-page1.jpg",
               "1": "image-for-page1.jpg",
               "2": "image-for-page2.jpg",
               "3": "image-for-page3.jpg"
           },

       "do-not-align":
           {
           "method": "remove",
           "segments":
               [
                   {   "begin": 1,     "end": 17000   },
                   {   "begin": 57456, "end": 68000   }
               ]
           }
   }

Warning: mind your commas! The JSON format is very picky: commas
separate elements in a list or dictionnary, but if you accidentally have
a comma after the last element (e.g., by cutting and pasting whole
lines), you will get a syntax error.

The g2p cascade
~~~~~~~~~~~~~~~

Sometimes the g2p conversion of the input text will not succeed, for
various reasons. A word might use characters not recognized by the g2p
for the language, or it might be in a different language. Whatever the
reason, the output for the g2p conversion will not be valid ARPABET, and
so the system will not be able to proceed to alignment by the readalongs
aligner, SoundSwallower.

If you know the language for that text, you can mark it as such in the
XML. E.g., ``<s xml:lang="eng">This sentence is in English.</s>``. The
``xml:lang`` attribute can be added to any element in the XML structure
and will apply to text at any depth within that element, unless the
attribute is specified again at a deeper level, e.g.,
``<s xml:lang="eng">English mixed with <foo xml:lang="fra">français</foo>.</s>``.

There is also a simpler option available: the g2p cascade. When the g2p
cascade is enabled, the g2p mapping will be done by first trying the
language specified in the XML file (or with the ``-l`` flag on the
command line, if the input is plain text). For each word where the
result is not valid ARPABET, the g2p mapping will be attempted again
with each of the languages specified in the g2p cascade, in order, until
a valid ARPABET conversion is obtained. If not valid conversion is
possible, are error message is printed and alignment is not attempted.

To enable the g2p cascade, add the ``--g2p-fallback l1:l2:...`` option
to ``readalongs g2p`` or ``readalongs align``:

::

   readalongs g2p --g2p-fallback fra:eng:und myfile.tokenize.xml myfile.g2p.xml
   readalongs align --g2p-fallback fra:eng:und myfile.xml myfile.wav output

The "Undetermined" language code: und
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Notice that the two examples above use ``und`` as the last language in the
cascade. ``und``, for Undetermined, is a special language mapping that
uses the Unicode definition of all known characters in all alphabets, and
maps them as if the name of that character was how it is pronounced.
While crude, this mapping works surprisingly well for the purposes of
forced alignment, and allows ``readalongs align`` to successfully align
most text with a few foreign words without any manual intervention. We
recommend systematically using ``und`` at the end of the cascade. Note
that adding another language after ``und`` will have no effect, since
the Undetermined mapping will map any string to valid ARPABET.

Debugging g2p mapping issues
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The warning messages issued by ``readalongs g2p`` and
``readalongs align`` indicate which words are causing g2p problems. It
can be worth inspecting to input text to fix any encoding or spelling
errors highlighted by these warnings. More detailed messages can be
produced by adding the ``--g2p-verbose`` switch, to obtain a lot more
information about g2p’ing words in each language g2p was unsucessfully
attempted.

Breaking up the pipeline
~~~~~~~~~~~~~~~~~~~~~~~~

Two commands were added to the CLI in the last year to break processing up step
by step.

The following series of commands:

::

   readalongs prepare -l lang  file.txt file.xml
   readalongs tokenize file.xml file.tokenized.xml
   readalongs g2p file.tokenized.xml file.g2p.xml
   readalongs align file.g2p.xml file.wav output

is equivalent to the single command:

::

   readalongs align -i -l lang file.txt file.wav output

except that when running the pipeline as four separate commands, you can
edit the XML files between each step to make any required adjustments
and corrections.

Anchors: marking known alignment points
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Long audio/text file pairs can sometimes be difficult to align
correctly, because the aligner might get lost part way through the
alignment process. Anchors can be used to tell the aligner about known
correspondance points between the text and the audio stream.

Anchor syntax
^^^^^^^^^^^^^

Anchors are inserted in the XML file (the output of
``readalongs prepare``, ``readalongs tokenize`` or ``readalongs g2p``)
using the following syntax: ``<anchor time="3.42s"/>`` or
``<anchor time="3420ms"/>``. The time can be specified in seconds (this
is the default) or milliseconds.

Anchors can be placed anywhere in the XML file: between/before/after any
element or text.

Example:

::

   <?xml version='1.0' encoding='utf-8'?> <TEI> <text xml:lang="eng"> <body>
       <anchor time="143ms"/>
       <div type="page">
       <p>
           <s>Hello.</s>
           <anchor time="1.62s"/>
           <s>This is <anchor time="3.81s"/> <anchor time="3.94s"/> a test</s>
           <s><anchor time="4123ms"/>weirdword<anchor time="4789ms"/></s>
       </p>
       </div>
       <anchor time="6.74s"/>
   </body> </text> </TEI>

Anchor semantics
^^^^^^^^^^^^^^^^

When anchors are used, the alignment task is divided at each anchor,
creating a series of segments that are aligned independently from one
another. When alignment is performed, the aligner sees only the audio
and the text from the segment being processed, and the results are
joined together afterwards.

The beginning and end of files are implicit anchors: *n* anchors define
*n+1* segments: from the beginning of the audio and text to the first
anchor, between pairs of anchors, and from the last anchor to the end of
the audio and text.

Special cases equivalent to do-not-align audio: - If an anchor occurs
before the first word in the text, the audio up to that anchor’s
timestamps is excluded from alignment. - If an anchor occurs after the
last word, the end of the audio is excluded from alignment. - If two
anchors occur one after the other, the time span between them in the
audio is excluded from alignment. Using anchors to define do-not-align
audio segments is effectively the same as marking them as "do-not-align"
in the ``config.json`` file, except that DNA segments declared using
anchors have a known alignment with respect to the text, while the
position of DNA segments declared in the config file are inferred by the
aligner.

Anchor use cases
^^^^^^^^^^^^^^^^

1. Alignment fails because the stream is too long or too difficult to
   align.

   When alignment fails, listen to the audio stream and try to identify
   where some words you can pick up start or end. Even if you don’t
   understand the language, there might be some words you’re able to
   pick up and use as anchors to help the aligner.

2. You already know where some words/sentences/paragraphs start or end,
   because the data came with some partial alignment information. For
   example, the data might come from an ELAN file with sentence
   alignments.

   These known timestamps can be converted to anchors.
