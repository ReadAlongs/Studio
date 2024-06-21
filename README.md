# ReadAlong-Studio

[![codecov](https://codecov.io/gh/ReadAlongs/Studio/branch/main/graph/badge.svg)](https://codecov.io/gh/ReadAlongs/Studio)
[![Build Status](https://github.com/readalongs/Studio/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/ReadAlongs/Studio/actions)
[![PyPI package](https://img.shields.io/pypi/v/readalongs.svg)](https://pypi.org/project/readalongs/)
[![Deploy web-api](https://img.shields.io/badge/%E2%86%91_Deploy_to-Heroku-7056bf.svg)](https://readalong-studio.herokuapp.com/api/v1/docs)
[![GitHub license](https://img.shields.io/github/license/ReadAlongs/Studio)](https://github.com/ReadAlongs/Studio/blob/main/LICENSE)
[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg)](https://github.com/ReadAlongs/Studio)
[![Documentation](https://github.com/ReadAlongs/studio/actions/workflows/docs.yml/badge.svg)](https://readalongs.github.io/Studio/)

> Audiobook alignment for Indigenous languages!

This library is an end-to-end audio/text aligner. It is meant to be used together with the [ReadAlong-Web-Component](https://github.com/roedoejet/ReadAlong-Web-Component) to interactively visualize the alignment.

## Table of Contents

- [ReadAlong-Studio](#readalong-studio)
  - [Table of Contents](#table-of-contents)
  - [Background](#background)
  - [Install](#install)
    - [Dependencies](#installing-dependencies)
    - [Studio itself](#Installing-ReadAlongs-Studio-itself)
    - [Validation](#Verifying-your-installation)
  - [Usage](#usage)
    - [CLI](#cli)
    - [Web API](#web-api)
    - [Studio](#studio-web-application)
    - [Docker](#docker)
  - [Maintainers](#maintainers)
  - [Contributing](#contributing)
    - [Contributors](#contributors)
  - [License](#license)

See also: [ReadAlong-Studio documentation](https://readalong-studio.readthedocs.io/en/latest/index.html).

## Background

The concept is a web application with a series of stages of
processing, which ultimately leads to a time-aligned audiobook -
i.e. a package of:

- ReadAlong XML file describing text
- Audio file (WAV or MP3)

Which can be loaded using the read-along [web component](https://github.com/roedoejet/ReadAlong-Web-Component). See also [Studio Output Realizations](https://readalong-studio.readthedocs.io/en/latest/outputs.html).

Optionally a book can be generated as a standalone HTML page, XHTML, Praat TextGrid, ELAN Eaf file, as well as WebVTT or SRT subitle formats.

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

### Installing dependencies

Before you can install the ReadAlong Studio, you will need to install these dependencies:

 - Python, version 3.8 or higher,
 - [FFmpeg](https://ffmpeg.org/),
 - a C compiler,
 - Git (optional, needed to get the current development version).

#### Dependencies on MacOS

First install Homebrew, then use it to install FFmpeg with `brew install ffmpeg`.

The compiler should already be on your machine.

Consider Xcode for your XML and text file editor.

#### Dependencies on Linux

If FFmpeg is not already installed, `<your package manager> install ffmpeg` should add it.

The compiler should already be there, but run `<your package manager> install gcc` if not.

#### Dependencies on Windows

##### The easy way, using Anaconda

Anaconda/Miniconda will install Python 3 and the required compiler automatically for you,
and simplifies ffmpeg and git installation. We recommend this solution.

Download and install the latest "Miniconda3 Windows 64-bit" installer from
https://docs.conda.io/en/latest/miniconda.html.
You can accept all the default options suggested by the installer.

Launch an Anaconda Prompt (this should be available from your Start menu after
installation) and run:

    conda install ffmpeg
    conda install git

You can then run the pip install and git commands below, and use readalongs, all from the Anaconda
Prompt.

##### The hard way

If you know what you're doing, you can install the dependencies directly on your machine:

 - Install Python3 for Windows.
 - Install [FFmpeg builds for Windows](https://ffmpeg.zeranoe.com/builds/) ([alternative instructions](https://windowsloop.com/install-ffmpeg-windows-10/)).
 - Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2017) (search for "Build Tools", select C++ when prompted).
 - Install Git for Windows (optional).

### Installing ReadAlongs Studio itself

To install the latest version of readalongs published to PyPI, you can run a standard pip
installation: `pip install readalongs`. Be warned, however, that this project is still very active so the published version could be out-of-date. Consider installing the current development version instead.

To install the current development version, clone the repo and pip install it
locally:

```sh
$ git clone https://github.com/ReadAlongs/Studio.git
$ cd Studio
$ pip install -e .
```

### Verifying your installation

Run `readalongs -h` to confirm that installation was successful.

If you installed the current development version with Git, you can also run the full test suite:

    cd Studio/test
    python run.py dev

And you can download our [open samples on GitHub](https://github.com/ReadAlongs/OpenSamples)
to run your first alignments.

## Usage

ReadAlong-Studio can be used either through the command line, a distributed web application or Docker.

### CLI

This page lists only the most basic commands.

For more information about how the command line interface works:
* Consult the [CLI User Guide](https://readalong-studio.readthedocs.io/en/latest/cli-guide.html).
* Consult the [CLI Reference](https://readalong-studio.readthedocs.io/en/latest/cli-ref.html).
* Invoke any CLI command with `-h` or `--help` for usage information. e.g., `readalongs --help`, `readalongs align --help`.

#### Alignment

Basic alignment is done with the following command.

`readalongs align TEXTFILE WAVFILE OUTPUTNAME`

### Web API

This page lists only the most basic commands.

For more information about how the command line interface works consult the interactive [API Documentation](https://readalong-studio.herokuapp.com/api/v1/docs).

For information on spinning up your own dev Web API server locally, have a look at [web\_api.py](readalongs/web_api.py), but briefly, if you are running it locally for development, use:

    DEVELOPMENT=1 uvicorn readalongs.web_api:web_api_app --reload

#### /langs

To query a list of available languages in the ReadAlong Studio API, send a GET request to https://readalongs-studio.herokuapp.com/api/v1/langs

#### /assemble

This endpoint is a remote procedural call that assembles the data needed to build a readalong using the JavaScript-based [SoundSwallower decoder](https://github.com/ReadAlongs/SoundSwallower). It is an endpoint that accepts POST requests with either plaintext or XML input. Please see the [documentation](https://readalong-studio.herokuapp.com/api/v1/docs) for more information.

### Studio web application

The ReadAlong-Studio web interface is available at https://readalong-studio.mothertongues.org/ and the source code is available here: https://github.com/ReadAlongs/Web-Component

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

## Maintainers

[@dhdaines](https://github.com/dhdaines).
[@littell](https://github.com/littell).
[@roedoejet](https://github.com/roedoejet).
[@joanise](https://github.com/joanise).

## Contributing

Feel free to dive in! [Open an issue](https://github.com/ReadAlongs/Studio/issues/new) or submit PRs.

This repo follows the [Contributor Covenant](http://contributor-covenant.org/version/1/3/0/) Code of Conduct.

You can install our standard Git hooks by running these commands in your sandbox:

```sh
pip install -r requirements.dev.txt
pre-commit install
gitlint install-hook
```

Have a look at [Contributing.md](Contributing.md) for the full details on the
Conventional Commit messages we prefer, our code formatting conventions, and
our Git hooks.

### Contributors

This project exists thanks to all the people who contribute.

Here is a partial list:
[@dhdaines](https://github.com/dhdaines).
[@eddieantonio](https://github.com/eddieantonio).
[@finguist](https://github.com/finguist).
[@joanise](https://github.com/joanise).
[@littell](https://github.com/littell).
[@roedoejet](https://github.com/roedoejet).

Project web page: [ReadAlong Studio: Application for Indigenous audiobooks and videos project](https://nrc.canada.ca/en/research-development/research-collaboration/programs/readalong-studio-application-indigenous-audiobooks-videos-project)

### Citation

if you use this software in a project of yours and write about it, please cite
us using the following:

Littell, P., Joanis, E., Pine, A., Tessier, M., Huggins-Daines, D., & Torkornoo, D. (2022). ReadAlong Studio: Practical Zero-Shot Text-Speech Alignment for Indigenous Language Audiobooks. Proceedings of SIGUL2022 @LREC2022, 23–32.

```
@inproceedings{Littell_ReadAlong_Studio_Practical_2022,
author = {Littell, Patrick and Joanis, Eric and Pine, Aidan and Tessier, Marc and Huggins-Daines, David and Torkornoo, Delasie},
booktitle = {Proceedings of SIGUL2022 @LREC2022},
title = {{ReadAlong Studio: Practical Zero-Shot Text-Speech Alignment for Indigenous Language Audiobooks}},
year = {2022},
month = {6},
pages = {23--32},
publisher = {European Language Resources Assiciation (ELRA)},
url = {https://aclanthology.org/2022.sigul-1.4}
}
```

Aidan Pine, David Huggins-Daines, Eric Joanis, Patrick Littell, Marc Tessier, Delasie Torkornoo, Rebecca Knowles, Roland Kuhn, and Delaney Lothian. 2023. ReadAlong Studio Web Interface for Digital Interactive Storytelling. In Proceedings of the 18th Workshop on Innovative Use of NLP for Building Educational Applications (BEA 2023), pages 163–172, Toronto, Canada. Association for Computational Linguistics.

```
@inproceedings{pine-etal-2023-readalong,
    title = "{R}ead{A}long Studio Web Interface for Digital Interactive Storytelling",
    author = "Pine, Aidan  and  Huggins-Daines, David  and  Joanis, Eric  and  Littell, Patrick  and  Tessier, Marc  and  Torkornoo, Delasie  and  Knowles, Rebecca  and  Kuhn, Roland  and  Lothian, Delaney",
    editor = {Kochmar, Ekaterina  and  Burstein, Jill  and  Horbach, Andrea  and  Laarmann-Quante, Ronja  and  Madnani, Nitin  and  Tack, Ana{\"\i}s  and  Yaneva, Victoria  and  Yuan, Zheng  and  Zesch, Torsten},
    booktitle = "Proceedings of the 18th Workshop on Innovative Use of NLP for Building Educational Applications (BEA 2023)",
    month = jul,
    year = "2023",
    address = "Toronto, Canada",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2023.bea-1.14",
    doi = "10.18653/v1/2023.bea-1.14",
    pages = "163--172",
    abstract = "We develop an interactive web-based user interface for performing textspeech alignment and creating digital interactive read-along audio books that highlight words as they are spoken and allow users to replay individual words when clicked. We build on an existing Python library for zero-shot multilingual textspeech alignment (Littell et al., 2022), extend it by exposing its functionality through a RESTful API, and rewrite the underlying speech recognition engine to run in the browser. The ReadAlong Studio Web App is open-source, user-friendly, prioritizes privacy and data sovereignty, allows for a variety of standard export formats, and is designed to work for the majority of the world{'}s languages.",
}
```

## License

[MIT](LICENSE) © 2019-2022 David Huggins-Daines and National Research Council Canada
