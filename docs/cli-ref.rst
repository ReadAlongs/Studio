.. _cli:

Command line interface (CLI)
============================

The CLI has two main commands: ``prepare`` and ``align``.

- If your data is a plain text file, you can run ``prepare`` to turn it into
  XML, which you can then align with ``align``. Doing this in two steps allows
  you to modify the XML file before aligning it (e.g., to mark that some text is
  in a different language, to flag some do-not-align text, or to drop anchors
  in).

- Alternatively, if your plain text file does not need to be modified, you can
  run ``align`` directly and use the ``-i`` option to indicate that the input
  is plain text and not xml. You'll also need the ``-l <language>`` option to
  indicate what language your text is in.

Two additional commands are sometimes useful: ``tokenize`` and ``g2p``.

- ``tokenize`` takes the output of ``prepare`` and tokenizes it, wrapping each
  word in the text in a ``<w>`` element.

- ``g2p`` takes the output of ``tokenize`` and mapping each word to its
  phonetic transcription using the g2p library. The phonetic transcription is
  represented using the ARPABET phonetic codes and are added in the ``ARPABET``
  attribute to each ``<w>`` element.

The result of ``tokenize`` or ``g2p`` can be fixed manually if necessary and
then used as input to ``align``.

Each command can be run with ``-h`` or ``--help`` to display its usage manual,
e.g., ``readalongs -h``, ``readalongs align --help``.


.. click:: readalongs.cli:align
  :prog: readalongs align

.. click:: readalongs.cli:prepare
  :prog: readalongs prepare

.. click:: readalongs.cli:tokenize
  :prog: readalongs tokenize

.. click:: readalongs.cli:g2p
  :prog: readalongs g2p
