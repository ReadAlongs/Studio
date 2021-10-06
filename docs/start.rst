.. start:

Getting Started
================

This library is an end-to-end audio/text aligner. It is meant to be used
together with the ReadAlong-Web-Component to interactively visualize the
alignment.

Background
----------

The concept is a web application with a series of stages of processing,
which ultimately leads to a time-aligned audiobook, i.e., a package of:

-  SMIL file describing time alignments
-  XML file describing text
-  Audio file (WAV or MP3)
-  HTML file describing the web component

Which can be loaded using the `read-along web
component <https://github.com/roedoejet/ReadAlong-Web-Component>`__.

A book is generated as a standalone HTML page by default, but can
optionally be generated as an ePub file.

Required knowledge
------------------

-  Command line interface (CLI)
-  Plain text file/xml/smil
-  Audacity or similar
-  Spinning up a server

What you need to make a ReadAlong
---------------------------------

In order to create a ReadAlong you will need two files:

- Plain text (``.txt``) or XML (``.xml``)
- Clear audio in any format supported by `ffmpeg <https://ffmpeg.org/ffmpeg-formats.html>`__

The content of the text file should be a transcription of the audio
file. The audio can be spoken or sung, but if there is background music
or noise of any kind, the aligner is likely to fail. Clearly enunciated
audio is also likely to increase accuracy.
