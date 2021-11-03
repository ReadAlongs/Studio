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
#    - prepare: prepare XML input for align from plain text
#    - tokenize: tokenize the prepared file
#    - g2p    : apply g2p to the tokenized file
#
#   Default CLI commands provided by Flask:
#    - routes : show available routes in the this readalongs Flask app
#    - run    : run the readalongs Flask app
#    - shell  : open a shell within the readalongs Flask application context
#
#######################################################################

import io
import json
import os
import sys
from tempfile import TemporaryFile

import click
from flask.cli import FlaskGroup
from lxml import etree

from readalongs._version import __version__
from readalongs.align import align_audio, create_input_tei, save_readalong
from readalongs.app import app
from readalongs.log import LOGGER
from readalongs.python_version import ensure_using_supported_python_version
from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.convert_xml import convert_xml
from readalongs.text.tokenize_xml import tokenize_xml
from readalongs.text.util import save_xml, write_xml
from readalongs.util import getLangs, parse_g2p_fallback

LANGS, _ = getLangs()
ensure_using_supported_python_version()


def create_app():
    """Returns the app"""
    return app


def get_click_file_name(click_file):
    """Wrapper around click_file.name with consistent handling for stdin

    On Windows, if click_file is stdin, click_file.name == "-".
    On Linux, if click_file is stdin, click_file.name == "<stdin>".
    During unit testing, the simulated stdin stream has no .name attribute.

    Args:
        click_file(click.File): the click file whose name we need

    Returns:
        "-" if click_file represents stdin, click_file.name otherwise
    """
    try:
        name = click_file.name
    except AttributeError:
        name = "-"
    return "-" if name == "<stdin>" else name


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.version_option(version=__version__, prog_name="readalongs")
@click.group(cls=FlaskGroup, create_app=create_app, context_settings=CONTEXT_SETTINGS)
def cli():
    """Management script for Read Along Studio."""


@app.cli.command(  # noqa C901
    context_settings=CONTEXT_SETTINGS, short_help="Force align a text and a sound file."
)
@click.argument("textfile", type=click.Path(exists=True, readable=True))
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
    help="Input is plain text (otherwise it’s assumed to be XML)",
)
@click.option(
    "-l",
    "--language",
    type=click.Choice(LANGS, case_sensitive=False),
    help="The language code for text in TEXTFILE (use only with -i, i.e., with plain text input)",
)
@click.option(
    "-s",
    "--save-temps",
    is_flag=True,
    help="Save intermediate stages of processing and temporary files (dictionary, FSG, tokenization, etc)",
)
@click.option(
    "-t", "--text-grid", is_flag=True, help="Export to Praat TextGrid & ELAN eaf file"
)
@click.option("-H", "--html", is_flag=True, help="Export to a single-file HTML format")
@click.option(
    "-x", "--output-xhtml", is_flag=True, help="Output simple XHTML instead of XML"
)
@click.option(
    "--g2p-fallback",
    default=None,
    help="Colon-separated list of fallback langs for g2p; enables the g2p cascade",
)
@click.option(
    "--g2p-verbose",
    is_flag=True,
    default=False,
    help="Display verbose g2p error messages",
)
def align(**kwargs):  # noqa: C901
    """Align TEXTFILE and AUDIOFILE and create output files as OUTPUT_BASE.* in directory
    OUTPUT_BASE/.

    TEXTFILE:    Input text file path (in XML, or plain text with -i)

    \b
    With -i, TEXTFILE should be plain text:
     - The text in TEXTFILE should be plain UTF-8 text without any markup.
     - Paragraph breaks are indicated by inserting one blank line.
     - Page breaks are indicated by inserting two blank lines.

    \b
    Without -i, TEXTFILE can be in one of three XML formats:
     - the output of 'readalongs prepare',
     - the output of 'readalongs tokenize', or
     - the output of 'readalongs g2p'.

    One can add the known ARPABET phonetics in the XML for words (<w> elements)
    that are not correctly handled by g2p in the output of 'readalongs tokenize'
    or 'readalongs g2p', via the ARPABET attribute.

    One can add anchor elements in the XML, e.g., '<anchor time="2.345s"/>', to
    mark known anchor points between the audio and text stream.

    AUDIOFILE:   Input audio file path, in any format supported by ffmpeg

    OUTPUT_BASE: Output files will be saved as OUTPUT_BASE/OUTPUT_BASE.*
    """
    config_file = kwargs.get("config", None)
    config = None
    if config_file:
        if config_file.endswith("json"):
            try:
                with open(config_file, encoding="utf8") as f:
                    config = json.load(f)
            except json.decoder.JSONDecodeError as e:
                raise click.BadParameter(
                    f"Config file at {config_file} is not in valid JSON format."
                ) from e
        else:
            raise click.BadParameter(
                f"Config file '{config_file}' must be in JSON format"
            )

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
    except Exception as e:
        raise click.UsageError(
            f"Cannot write into output folder '{output_dir}'. Please verify permissions."
        ) from e

    try:
        g2p_fallbacks = parse_g2p_fallback(kwargs["g2p_fallback"])
    except ValueError as e:
        raise click.BadParameter(e) from e

    output_basename = os.path.basename(output_dir)
    temp_base = None
    if kwargs["save_temps"]:
        temp_dir = os.path.join(output_dir, "tempfiles")
        if not os.path.isdir(temp_dir):
            if os.path.exists(temp_dir) and kwargs["force_overwrite"]:
                os.unlink(temp_dir)
            os.mkdir(temp_dir)
        temp_base = os.path.join(temp_dir, output_basename)

    if kwargs["debug"]:
        LOGGER.setLevel("DEBUG")

    if kwargs["text_input"]:
        if not kwargs["language"]:
            raise click.BadParameter(
                "No input language specified for plain text input. Please provide the -l/--language switch."
            )
        plain_textfile = kwargs["textfile"]
        _, xml_textfile = create_input_tei(
            input_file_name=plain_textfile,
            text_language=kwargs["language"],
            save_temps=temp_base,
        )
    else:
        xml_textfile = kwargs["textfile"]

    bare = kwargs.get("bare", False)

    try:
        results = align_audio(
            xml_textfile,
            kwargs["audiofile"],
            bare=bare,
            config=config,
            save_temps=temp_base,
            g2p_fallbacks=g2p_fallbacks,
            verbose_g2p_warnings=kwargs["g2p_verbose"],
        )
    except RuntimeError as e:
        LOGGER.error(e)
        sys.exit(1)
    save_readalong(
        align_results=results,
        output_dir=output_dir,
        output_basename=output_basename,
        config=config,
        text_grid=kwargs["text_grid"],
        closed_captioning=kwargs["closed_captioning"],
        output_xhtml=kwargs["output_xhtml"],
        audiofile=kwargs["audiofile"],
        audiosegment=results["audio"],
        html=kwargs["html"],
    )


@app.cli.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Convert a plain text file into the XML format for alignment.",
)
@click.argument("plaintextfile", type=click.File("r", encoding="utf8", lazy=True))
@click.argument("xmlfile", type=click.Path(), required=False, default="")
@click.option("-d", "--debug", is_flag=True, help="Add debugging messages to logger")
@click.option(
    "-f", "--force-overwrite", is_flag=True, help="Force overwrite output files"
)
@click.option(
    "-l",
    "--language",
    type=click.Choice(LANGS, case_sensitive=False),
    required=True,
    help="The language code for text in PLAINTEXTFILE",
)
def prepare(**kwargs):
    """Prepare XMLFILE for 'readalongs align' from PLAINTEXTFILE.
    PLAINTEXTFILE must be plain text encoded in UTF-8, with one sentence per line,
    paragraph breaks marked by a blank line, and page breaks marked by two
    blank lines.

    PLAINTEXTFILE: Path to the plain text input file, or - for stdin

    XMLFILE:       Path to the XML output file, or - for stdout [default: PLAINTEXTFILE.xml]
    """

    if kwargs["debug"]:
        LOGGER.setLevel("DEBUG")
        LOGGER.info(
            "Running readalongs prepare(lang={}, force-overwrite={}, plaintextfile={}, xmlfile={}).".format(
                kwargs["language"],
                kwargs["force_overwrite"],
                kwargs["plaintextfile"],
                kwargs["xmlfile"],
            )
        )

    input_file = kwargs["plaintextfile"]

    out_file = kwargs["xmlfile"]
    if not out_file:
        out_file = get_click_file_name(input_file)
        if out_file != "-":
            if out_file.endswith(".txt"):
                out_file = out_file[:-4]
            out_file += ".xml"

    if out_file == "-":
        _, filename = create_input_tei(
            input_file_handle=input_file, text_language=kwargs["language"],
        )
        with io.open(filename, encoding="utf8") as f:
            sys.stdout.write(f.read())
    else:
        if not out_file.endswith(".xml"):
            out_file += ".xml"
        if os.path.exists(out_file) and not kwargs["force_overwrite"]:
            raise click.BadParameter(
                "Output file %s exists already, use -f to overwrite." % out_file
            )

        _, filename = create_input_tei(
            input_file_handle=input_file,
            text_language=kwargs["language"],
            output_file=out_file,
        )

    LOGGER.info("Wrote {}".format(out_file))


@app.cli.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Tokenize a prepared XML file, in preparation for alignment.",
)
@click.argument("xmlfile", type=click.File("rb"))
@click.argument("tokfile", type=click.Path(), required=False, default="")
@click.option("-d", "--debug", is_flag=True, help="Add debugging messages to logger")
@click.option(
    "-f", "--force-overwrite", is_flag=True, help="Force overwrite output files"
)
def tokenize(**kwargs):
    """Tokenize XMLFILE for 'readalongs align' into TOKFILE.
    XMLFILE should have been produced by 'readalongs prepare'.
    TOKFILE can then be augmented with word-specific language codes.
    'readalongs align' can be called with either XMLFILE or TOKFILE as XML input.

    XMLFILE: Path to the XML file to tokenize, or - for stdin

    TOKFILE: Output path for the tok'd XML, or - for stdout [default: XMLFILE.tokenized.xml]
    """

    if kwargs["debug"]:
        LOGGER.setLevel("DEBUG")
        LOGGER.info(
            "Running readalongs tokenize(xmlfile={}, tokfile={}, force-overwrite={}).".format(
                kwargs["xmlfile"], kwargs["tokfile"], kwargs["force_overwrite"],
            )
        )

    input_file = kwargs["xmlfile"]

    if not kwargs["tokfile"]:
        output_path = get_click_file_name(input_file)
        if output_path != "-":
            if output_path.endswith(".xml"):
                output_path = output_path[:-4]
            output_path += ".tokenized.xml"
    else:
        output_path = kwargs["tokfile"]
        if not output_path.endswith(".xml") and not output_path == "-":
            output_path += ".xml"

    if os.path.exists(output_path) and not kwargs["force_overwrite"]:
        raise click.BadParameter(
            "Output file %s exists already, use -f to overwrite." % output_path
        )

    try:
        xml = etree.parse(input_file).getroot()
    except etree.XMLSyntaxError as e:
        raise click.BadParameter(
            "Error parsing input file %s as XML, please verify it. Parser error: %s"
            % (get_click_file_name(input_file), e)
        )

    # Tokenize the XML file - all this code for such a tiny body!!!
    xml = tokenize_xml(xml)

    if output_path == "-":
        write_xml(sys.stdout.buffer, xml)
    else:
        save_xml(output_path, xml)
    LOGGER.info("Wrote {}".format(output_path))


@app.cli.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Apply g2p to a tokenized file, like 'align' does.",
    # NOT TRUE YET: "Apply g2p to a tokenized file, in preparation for alignment."
)
@click.argument("tokfile", type=click.File("rb", encoding="utf8", lazy=True))
@click.argument("g2pfile", type=click.Path(), required=False, default="")
@click.option(
    "--g2p-fallback",
    default=None,
    help="Colon-separated list of fallback langs for g2p; enables the g2p cascade",
)
@click.option(
    "-f", "--force-overwrite", is_flag=True, help="Force overwrite output files"
)
@click.option(
    "--g2p-verbose",
    is_flag=True,
    default=False,
    help="Display verbose messages about g2p errors.",
)
@click.option("-d", "--debug", is_flag=True, help="Add debugging messages to logger")
def g2p(**kwargs):
    """Apply g2p mappings to TOKFILE into G2PFILE.
    TOKFILE should have been produced by 'readalongs tokenize'.
    G2PFILE can then be modified to adjust the phonetic representation as needed.
    'readalongs align' can be called with G2PFILE instead of TOKFILE as XML input.

    WARNING: the output is not yet compatible with align and cannot be used as input to align.

    TOKFILE: Path to the input tokenized XML file, or - for stdin

    G2PFILE: Output path for the g2p'd XML, or - for stdout [default: TOKFILE with .g2p. inserted]
    """
    if kwargs["debug"]:
        LOGGER.setLevel("DEBUG")
        LOGGER.info(
            "Running readalongs g2p(tokfile={}, g2pfile={}, force-overwrite={}).".format(
                kwargs["tokfile"], kwargs["g2pfile"], kwargs["force_overwrite"],
            )
        )

    input_file = kwargs["tokfile"]

    if not kwargs["g2pfile"]:
        output_path = get_click_file_name(input_file)
        if output_path != "-":
            if output_path.endswith(".xml"):
                output_path = output_path[:-4]
            if output_path.endswith(".tokenized"):
                output_path = output_path[: -len(".tokenized")]
            output_path += ".g2p.xml"
    else:
        output_path = kwargs["g2pfile"]
        if not output_path.endswith(".xml") and not output_path == "-":
            output_path += ".xml"

    if os.path.exists(output_path) and not kwargs["force_overwrite"]:
        raise click.BadParameter(
            "Output file %s exists already, use -f to overwrite." % output_path
        )

    try:
        xml = etree.parse(input_file).getroot()
    except etree.XMLSyntaxError as e:
        raise click.BadParameter(
            "Error parsing input file %s as XML, please verify it. Parser error: %s"
            % (get_click_file_name(input_file), e)
        )

    try:
        g2p_fallbacks = parse_g2p_fallback(kwargs["g2p_fallback"])
    except ValueError as e:
        raise click.BadParameter(e) from e

    # Add the IDs to paragraph, sentences, word, etc.
    xml = add_ids(xml)

    # Apply the g2p mappings.
    xml, valid = convert_xml(
        xml, g2p_fallbacks=g2p_fallbacks, verbose_warnings=kwargs["g2p_verbose"],
    )

    if output_path == "-":
        write_xml(sys.stdout.buffer, xml)
    else:
        save_xml(output_path, xml)
        LOGGER.info("Wrote {}".format(output_path))

    if not valid:
        LOGGER.error(
            "Some word(s) could not be g2p'd correctly."
            + (
                " Run again with --g2p-verbose to get more detailed error messages."
                if not kwargs["g2p_verbose"]
                else ""
            )
        )
        sys.exit(1)
