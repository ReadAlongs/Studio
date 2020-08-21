#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# cli.py
#
#   Initializes a Command Line Interface with Click.
#   The main purpose of the cli is to align input files.
#
#   CLI commands implemented in this file:
#    - align  : main command to align text and audio
#    - epub   : convert aligned file to epub format
#    - prepare: prepare XML input for align from plain text
#
#   Default CLI commands provided by Flask:
#    - routes : show available routes in the this readalongs Flask app
#    - run    : run the readalongs Flask app
#    - shell  : open a shell within the readalongs Flask application context
#
#######################################################################

import os
import json
import shutil
from tempfile import TemporaryFile

import click
from networkx import has_path
from flask.cli import FlaskGroup
from g2p.mappings.langs import LANGS_AVAILABLE, LANGS_NETWORK

from readalongs.app import app
from readalongs.log import LOGGER
from readalongs.align import align_audio
from readalongs._version import __version__
from readalongs.text.make_smil import make_smil
from readalongs.text.util import save_xml, save_txt
from readalongs.epub.create_epub import create_epub
from readalongs.align import write_to_subtitles, write_to_text_grid
from readalongs.align import (
    create_input_tei,
    convert_to_xhtml,
    return_words_and_sentences,
)
from readalongs.audio_utils import read_audio_from_file


# get the key from all networks in text module that have a path to 'eng-arpabet'
# which is needed for the readalongs
LANGS = [
    k
    for x in LANGS_AVAILABLE
    for k in x.keys()
    if LANGS_NETWORK.has_node(k) and has_path(LANGS_NETWORK, k, "eng-arpabet")
]

# Hack to allow old English LexiconG2P
LANGS += ["eng"]


def create_app():
    """ Returns the app
    """
    return app


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.version_option(version=__version__, prog_name="readalongs")
@click.group(cls=FlaskGroup, create_app=create_app, context_settings=CONTEXT_SETTINGS)
def cli():
    """Management script for Read Along Studio."""


@app.cli.command(
    context_settings=CONTEXT_SETTINGS, short_help="Force align a text and a sound file."
)
@click.argument("inputfile", type=click.Path(exists=True, readable=True))
@click.argument("audiofile", type=click.Path(exists=True, readable=True))
@click.argument("output-base", type=click.Path())
@click.option(
    "-b",
    "--bare",
    is_flag=True,
    help="Bare alignments do not split silences between words",
)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True),
    help="Use ReadAlong-Studio configuration file (in JSON format)",
)
@click.option(
    "-C",
    "--closed-captioning",
    is_flag=True,
    help="Export sentences to WebVTT and SRT files",
)
@click.option("-d", "--debug", is_flag=True, help="Add debugging messages to logger")
@click.option(
    "-f", "--force-overwrite", is_flag=True, help="Force overwrite output files"
)
@click.option(
    "-i",
    "--text-input",
    is_flag=True,
    help="Input is plain text (assume paragraphs are separated by blank lines, pages are separated by two blank lines)",
)
@click.option(
    "-l",
    "--language",
    type=click.Choice(LANGS, case_sensitive=False),
    help="Set language for plain text input",
)
@click.option(
    "-u",
    "--unit",
    type=click.Choice(["w", "m"], case_sensitive=False),
    help="Unit (w = word, m = morpheme) to align to",
)
@click.option(
    "-s",
    "--save-temps",
    is_flag=True,
    help="Save intermediate stages of processing and temporary files (dictionary, FSG, tokenization etc)",
)
@click.option(
    "-t", "--text-grid", is_flag=True, help="Export to Praat TextGrid & ELAN eaf file"
)
@click.option(
    "-x", "--output-xhtml", is_flag=True, help="Output simple XHTML instead of XML"
)
def align(**kwargs):
    """Align INPUTFILE and AUDIOFILE and create output files at OUTPUT_BASE.

    inputfile : A path to the input text file (in XML, or plain text with -i option)

    audiofile : A path to the input audio file. Can be any format supported by ffmpeg

    output-base : A base name for output files
    """
    config = kwargs.get("config", None)
    if config:
        if config.endswith("json"):
            try:
                with open(config) as f:
                    config = json.load(f)
            except json.decoder.JSONDecodeError:
                LOGGER.error(f"Config file at {config} is not valid json.")
        else:
            raise click.BadParameter(f"Config file '{config}' must be in JSON format")

    output_dir = kwargs["output_base"]
    if os.path.exists(output_dir):
        if not os.path.isdir(output_dir):
            raise click.UsageError(
                f"Output folder '{output_dir}' already exists but is a not a directory."
            )
        if not kwargs["force_overwrite"]:
            raise click.UsageError(
                f"Output folder '{output_dir}' already exists, use -f to overwrite."
            )
    else:
        os.mkdir(output_dir)

    # Make sure we can write to the output directory, for early error checking and user
    # friendly error messages.
    try:
        with TemporaryFile(dir=output_dir):
            pass
    except Exception:
        raise click.UsageError(
            f"Cannot write into output folder '{output_dir}'. Please verify permissions."
        )

    output_base = os.path.join(output_dir, os.path.basename(output_dir))

    if kwargs["debug"]:
        LOGGER.setLevel("DEBUG")
    if kwargs["text_input"]:
        if not kwargs["language"]:
            LOGGER.warn("No input language provided, using undetermined mapping")
        tempfile, kwargs["inputfile"] = create_input_tei(
            kwargs["inputfile"],
            text_language=kwargs["language"],
            save_temps=(output_base if kwargs["save_temps"] else None),
        )
    if kwargs["output_xhtml"]:
        tokenized_xml_path = "%s.xhtml" % output_base
    else:
        _, input_ext = os.path.splitext(kwargs["inputfile"])
        tokenized_xml_path = "%s%s" % (output_base, input_ext)
    if os.path.exists(tokenized_xml_path) and not kwargs["force_overwrite"]:
        raise click.BadParameter(
            "Output file %s exists already, use -f to overwrite." % tokenized_xml_path
        )
    smil_path = output_base + ".smil"
    if os.path.exists(smil_path) and not kwargs["force_overwrite"]:
        raise click.BadParameter(
            "Output file %s exists already, use -f to overwrite." % smil_path
        )
    _, audio_ext = os.path.splitext(kwargs["audiofile"])
    audio_path = output_base + audio_ext
    if os.path.exists(audio_path) and not kwargs["force_overwrite"]:
        raise click.BadParameter(
            "Output file %s exists already, use -f to overwrite." % audio_path
        )
    unit = kwargs.get("unit", "w")
    bare = kwargs.get("bare", False)
    if (
        not unit
    ):  # .get() above should handle this but apparently the way kwargs is implemented
        unit = "w"  # unit could still be None here.
    try:
        results = align_audio(
            kwargs["inputfile"],
            kwargs["audiofile"],
            unit=unit,
            bare=bare,
            config=config,
            save_temps=(output_base if kwargs["save_temps"] else None),
        )
    except RuntimeError as e:
        LOGGER.error(e)
        exit(1)

    if kwargs["text_grid"]:
        audio = read_audio_from_file(kwargs["audiofile"])
        duration = audio.frame_count() / audio.frame_rate
        words, sentences = return_words_and_sentences(results)
        textgrid = write_to_text_grid(words, sentences, duration)
        textgrid.to_file(output_base + ".TextGrid")
        textgrid.to_eaf().to_file(output_base + ".eaf")

    if kwargs["closed_captioning"]:
        words, sentences = return_words_and_sentences(results)
        webvtt_sentences = write_to_subtitles(sentences)
        webvtt_sentences.save(output_base + "_sentences.vtt")
        webvtt_sentences.save_as_srt(output_base + "_sentences.srt")
        webvtt_words = write_to_subtitles(words)
        webvtt_words.save(output_base + "_words.vtt")
        webvtt_words.save_as_srt(output_base + "_words.srt")

    if kwargs["output_xhtml"]:
        convert_to_xhtml(results["tokenized"])

    save_xml(tokenized_xml_path, results["tokenized"])
    smil = make_smil(
        os.path.basename(tokenized_xml_path), os.path.basename(audio_path), results
    )
    shutil.copy(kwargs["audiofile"], audio_path)
    save_txt(smil_path, smil)


@app.cli.command(
    context_settings=CONTEXT_SETTINGS, short_help="Convert a smil document to epub."
)
@click.argument("input", type=click.Path(exists=True, readable=True))
@click.argument("output", type=click.Path(exists=False, readable=True))
@click.option(
    "-u",
    "--unpacked",
    is_flag=True,
    help="Output unpacked directory of files (for testing)",
)
def epub(**kwargs):
    """
    Convert INPUT smil document to epub with media overlay at OUTPUT

    input : the .smil document

    output : the path to the .epub output
    """
    create_epub(kwargs["input"], kwargs["output"], kwargs["unpacked"])


@app.cli.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Prepare XML input to align from plain text.",
)
@click.argument("inputfile", type=click.Path(exists=True, readable=True))
@click.argument("xmlfile", type=click.Path())
@click.option("-d", "--debug", is_flag=True, help="Add debugging messages to logger")
@click.option(
    "-f", "--force-overwrite", is_flag=True, help="Force overwrite output files"
)
@click.option(
    "-l",
    "--language",
    type=click.Choice(LANGS, case_sensitive=False),
    required=True,
    help="Set language for input file",
)
def prepare(**kwargs):
    """Prepare XMLFILE for 'readalongs align' from plain text INPUTFILE.
    INPUTFILE must be plain text encoded in utf-8, with one sentence per line,
    paragraph breaks marked by a blank line, and page breaks marked by two
    blank lines.

    inputfile : A path to the plain text input file

    xmlfile : File name for the .xml output file
    """
    if kwargs["debug"]:
        LOGGER.setLevel("DEBUG")
        LOGGER.info(
            "Running readalongs prepare(lang={}, force-overwrite={}, inputfile={}, xmlfile={}).".format(
                kwargs["language"],
                kwargs["force_overwrite"],
                kwargs["inputfile"],
                kwargs["xmlfile"],
            )
        )

    xmlpath = kwargs["xmlfile"]
    if not xmlpath.endswith(".xml"):
        xmlpath += ".xml"
    if os.path.exists(xmlpath) and not kwargs["force_overwrite"]:
        raise click.BadParameter(
            "Output file %s exists already, use -f to overwrite." % xmlpath
        )
    filehandle, filename = create_input_tei(
        kwargs["inputfile"], text_language=kwargs["language"], output_file=xmlpath
    )
    LOGGER.info("Wrote {}".format(xmlpath))
