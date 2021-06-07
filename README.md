# ReadAlong-Studio

[![codecov](https://codecov.io/gh/ReadAlongs/Studio/branch/master/graph/badge.svg)](https://codecov.io/gh/ReadAlongs/Studio)
[![Build Status](https://travis-ci.com/ReadAlongs/Studio.svg?branch=master)](https://travis-ci.com/ReadAlongs/Studio)
[![PyPI package](https://img.shields.io/pypi/v/readalongs.svg)](https://pypi.org/project/readalongs/)
[![GitHub license](https://img.shields.io/github/license/ReadAlongs/Studio)](https://github.com/ReadAlongs/Studio/blob/master/LICENSE)
[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=flat-square)](https://github.com/ReadAlongs/Studio)

:warning: :construction: This repo is currently **under construction** and is not stable. :construction: :warning:

> Audiobook alignment for Indigenous languages!

This library is an end-to-end audio/text aligner. It is meant to be used together with the [ReadAlong-Web-Component](https://github.com/roedoejet/ReadAlong-Web-Component) to interactively visualize the alignment.

## Table of Contents
- [ReadAlong-Studio](#readalong-studio)
  - [Table of Contents](#table-of-contents)
  - [Background](#background)
  - [Install](#install)
  - [Usage](#usage)
    - [CLI](#cli)
    - [Studio](#studio)
    - [Docker](#docker)
  - [Maintainers](#maintainers)
  - [Contributing](#contributing)
    - [Contributors](#contributors)
  - [License](#license)

Note: additional draft documentation is available [here](https://github.com/finguist/ReadAlong-Studio-Documentation/blob/main/prepare.md)

## Background

The concept is a web application with a series of stages of
processing, which ultimately leads to a time-aligned audiobook -
i.e. a package of:

- SMIL file describing time alignments
- TEI file describing text
- Audio file (WAV or MP3)

Which can be loaded using the read-along [web component](https://github.com/roedoejet/ReadAlong-Web-Component).

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

## Install

The best thing to do is install with pip `pip install readalongs`.

Otherwise, clone the repo and pip install it locally.

```sh
$ git clone https://github.com/ReadAlongs/Studio.git
$ cd Studio
$ pip install -e .
```

If you don't already have it, you will also need [FFmpeg](https://ffmpeg.org/).
 - Windows: [FFmpeg builds for Windows](https://ffmpeg.zeranoe.com/builds/) ([helpful instructions](https://windowsloop.com/install-ffmpeg-windows-10/))
 - Mac: `brew install ffmpeg`
 - Linux: `<your package manager> install ffmpeg`

On Windows, you might also need [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2017) (search for "Build Tools", select C++ when prompted) and [swigwin](http://www.swig.org/download.html).
(TODO: verify whether these are still needed now that `soundswallower` has replaced `pocketsphinx`.)

## Usage

ReadAlong-Studio can be used either through the command line, a distributed web application or Docker.

### CLI

Below shows some basic commands. For more information about how the command line interface works, please check this [incomplete documentation](https://readalong-studio.readthedocs.io/en/latest/index.html) and [this draft documentation](https://github.com/finguist/ReadAlong-Studio-Documentation/blob/main/prepare.md) [TODO: complete and fix all this documentation!]. Additionally, you can add the `--help` flag to any command for more information.

#### Alignment

Basic alignment is done with the following command.

`readalongs align TEXTFILE WAVFILE OUTPUTNAME`

#### ePub

In order to generate an ePub, there are two steps:

1. `readalongs align --output-xhtml TEXTFILE WAVFILE OUTPUTNAME`
2. `readalongs epub OUTPUTNAME.smil OUTPUTNAME.epub`

### Studio web application

ReadAlong-Studio has a web interface for creating interactive audiobooks. The web app can be served by first installing ReadAlong-Studio and then running `readalongs run`. A web app will then be available on port 5000.

### Docker

If you are having trouble installing the package, you can also clone the repo and run the studio using Docker.

To build the Docker container, run:

    docker build . --tag=readalong-studio

To run the Flask web app from the Docker container:

    docker run -p 5000:5000 -it readalong-studio

Then you should be able to visit http://localhost:5000/.


## Maintainers

[@dhdaines](https://github.com/dhdaines).
[@littell](https://github.com/littell).
[@roedoejet](https://github.com/roedoejet).
[@joanise](https://github.com/joanise).

## Contributing

Feel free to dive in! [Open an issue](https://github.com/ReadAlongs/Studio/issues/new) or submit PRs.

This repo follows the [Contributor Covenant](http://contributor-covenant.org/version/1/3/0/) Code of Conduct.

Have a look at [Contributing.md](Contributing.md) for help getting started.

### Contributors

This project exists thanks to all the people who contribute.

[@dhdaines](https://github.com/dhdaines).
[@eddieantonio](https://github.com/eddieantonio).
[@finguist](https://github.com/finguist).
[@joanise](https://github.com/joanise).
[@littell](https://github.com/littell).
[@roedoejet](https://github.com/roedoejet).

## License

[MIT](LICENSE) © David Huggins-Daines, National Research Council Canada
