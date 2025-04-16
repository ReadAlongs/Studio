# Getting Started

This library is an end-to-end audio/text aligner. It is meant to be used
together with the ReadAlong-Web-Component to interactively visualize the
alignment.

## Background

The concept is a web application with a series of stages of processing,
which ultimately leads to a time-aligned audiobook, i.e., a www bundle of:

- ReadAlong XML file describing text and alignment
- Audio file (WAV or MP3)
- HTML file describing the web component

Which is displayed using the [read-along web
component](https://github.com/ReadAlongs/Studio-Web/tree/main/packages/web-component).

A book is generated as a standalong Offline HTML page and a www bundle by default,
but can optionally be generated as ELAN, Praat or subtitle files.

## Required knowledge

- How to use a [Command-line interface (CLI)](https://en.wikipedia.org/wiki/Command-line_interface).
- How to edit and manipulate plain text and [XML](https://www.w3.org/standards/xml/core) files using a text editor or a code editor.
- How to edit and examine an audio file with [Audacity](https://www.audacityteam.org/) or similar software.
- How to spin up a local web server (e.g., see [How do you set up a local testing server?](https://developer.mozilla.org/en-US/docs/Learn/Common_questions/set_up_a_local_testing_server))

## What you need to make a ReadAlong

In order to create a ReadAlong you will need two files:

- A text file, either in plain text (`.txt`) or in ReadAlong XML (`.readalong`)
- Clear audio in any format supported by [ffmpeg](https://ffmpeg.org/ffmpeg-formats.html)

The content of the text file should be a transcription of the audio
file. The audio can be spoken or sung, but if there is background music
or noise of any kind, the aligner might have a harder time. Clearly enunciated
audio is also likely to increase accuracy.
