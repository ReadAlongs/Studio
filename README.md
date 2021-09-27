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

Which can be loaded using the read-along [web component](https://github.com/roedoejet/ReadAlong-Web-Component). See also [Studio Output Realizations](docs/outputs.rst).

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

You will need: **Python 3.7 or higher**.

To install the latest version published to PyPI, you can run a standard pip
installation: `pip install readalongs`.

To install the current development version, clone the repo and pip install it
locally:

```sh
$ git clone https://github.com/ReadAlongs/Studio.git
$ cd Studio
$ pip3 install -e .
```

If you don't already have it, you will also need [FFmpeg](https://ffmpeg.org/).

- Windows: [FFmpeg builds for Windows](https://ffmpeg.zeranoe.com/builds/) ([helpful instructions](https://windowsloop.com/install-ffmpeg-windows-10/))
- Mac: `brew install ffmpeg`
- Linux: `<your package manager> install ffmpeg`

On Windows, you might also need [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2017) (search for "Build Tools", select C++ when prompted).

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

If you are having trouble installing the package, you can also clone the repo and run the
studio using Docker.

Working with in a Docker container has the advantage that no matter what your OS is, and
what you have installed or configured, you will run on the standard ReadAlong-Studio
configuration.

To build the Docker image, run:

    docker build . --tag=readalong-studio

To run the Flask web app in a Docker container using that image:

    docker run -p 5000:5000 -it readalong-studio

To run the Flask web app with real-time update:

    docker run -p 5000:5000 -it -v $(pwd):/opt/readalong-studio readalong-studio

Then you should be able to visit http://localhost:5000/.

To run the interactive shell with real-time update:

    docker run -p 5000:5000 -it -v $(pwd):/opt/readalong-studio readalong-studio sh

To run an interactive bash shell, using your local user inside Docker:

    docker run -p 5000:5000 -it -v $(pwd):/opt/readalong-studio -u $(id -u):$(id -g) readalong-studio bash

## Example Run:

```sh
2001  cd Studio/
2002  cd test
2007  readalongs -h
2008  readalongs align -h
2009  ls data
2010  cat data/ej-fra.txt
2011  readalongs align -l fra -i data/ej-fra.txt data/ej-fra.m4a output-for-mrw
2012  ls output-for-mrw/
2015  less output-for-mrw.xml
2017  less output-for-mrw.smil
2019  cd ..
2020  readalongs prepare -h
2022  readalongs prepare -l fra data/ej-fra.txt -
2027  less output-for-mrw/output-for-mrw.smil
2028  less output-for-mrw/output-for-mrw.xml
2029  readalongs prepare -l fra data/ej-fra.txt ej-prep.xml
2030  cat ej-prep.xml
2031  readalongs tokenize ej-prep.xml ej-tok.xml
2032  cat ej-tok.xml
2033  readalongs g2p ej-tok.xml ej-g2p.xml
2034  cat ej-g2p.xml
2024  vi data/patrickxtlan.xml
2036  readalongs g2p data/patrickxtlan.xml  -
2037  g2p convert travaille fra fra-ipa
2038  g2p convert travaille fra eng-arpabet

2013  cd output-for-mrw/
2041  python3 -m http.server
      # open brower to hostname:8000 to view this read-along
```

Notice that you may need to install develop version `g2p` package to make this example work.

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
