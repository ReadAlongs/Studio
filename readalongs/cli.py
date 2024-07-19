"""Readalongs command line interfaced, initialized with Click.

The main purpose of the cli is to align text and audio files

CLI commands implemented in this file:
 - align   : main command to align text and audio
 - make-xml : make XML input for align from plain text
 - tokenize: tokenize the XML file
 - g2p     : apply g2p to the tokenized file
 - langs   : list languages supported by align
"""

import io
import os
import sys

import click

from readalongs._version import VERSION
from readalongs.util import (
    JoinerCallbackForClick,
    get_langs,
    get_langs_deferred,
    get_obsolete_callback_for_click,
)

SUPPORTED_OUTPUT_FORMATS = {
    "eaf": "ELAN file",
    "html": "Single-file, offline HTML",
    "srt": "SRT subtitle",
    "TextGrid": "Praat TextGrid",
    "vtt": "WebVTT subtitle",
    "xhtml": "Simple XHTML",
}

SUPPORTED_OUTPUT_FORMATS_DESC = ", ".join(
    k + f" ({v})" for k, v in SUPPORTED_OUTPUT_FORMATS.items()
)


if "pytest" not in sys.modules:  # pragma: no cover
    if sys.stdout.encoding != "utf8" and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf8")
    if sys.stderr.encoding != "utf8" and hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf8")


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


@click.version_option(version=VERSION, prog_name="readalongs")
@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """Management script for ReadAlong Studio.

    \b
    This library helps you do text-audio alignment for many languages.
    The primary purpose is for creating 'readalong' interactive audiobooks,
    although other output formats like subtitles or Praat TextGrids are available.

    You can use this command line tool in two ways. The "end-to-end" method with the
    "align" command, or using a sequence of steps with "make-xml", "tokenize", and "g2p"
    to get more control over the process.

    ## End-to-End

    \b
    align
    =====
    To get started, you must have some audio and some corresponding text.
    This command will let you go 'end-to-end' from audio & text to readalongs.
    For more info, please see the help message for this command by running
    "readalongs align -h"

    ## Step-by-Step

    Using ReadAlongs this way, you must use the following commands in sequence.

    \b
    make-xml
    =======
    If you have plain text and you want to mark up some of the XML, you can
    use this command to turn your plain text into the XML structure
    used by readalongs.

    \b
    tokenize
    ========
    Use this command to tokenize the output of the previous "readalongs make-xml" command.

    \b
    g2p
    ===
    Use this command to apply the g2p rules necessary to convert the output of the
    "readalongs tokenize" command into a pronunciation form for the readalongs aligner.

    Finally, you can run "readalongs align" on the output of any of these commands to create
    the alignment files.

    For more info on any command in this interface, run it with "-h" to display
    its help message.
    """


@cli.command(  # type: ignore  # noqa: C901  # some versions of flake8 need this here
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
    "-o",
    "--output-formats",
    multiple=True,
    callback=JoinerCallbackForClick(SUPPORTED_OUTPUT_FORMATS, drop_case=True),
    help=(
        "Comma- or colon-separated list of additional output file formats to export to. "
        "The text is always exported as XML and alignments as SMIL, but "
        "one or more of these formats can be requested in addition:\b \n\n"
        + SUPPORTED_OUTPUT_FORMATS_DESC
    ),
)
@click.option(
    "-f", "--force-overwrite", is_flag=True, help="Force overwrite output files"
)
@click.option(
    "-i",
    "--text-input",
    hidden=True,
    is_flag=True,
    default=None,
    help="OBSOLETE; the input format is now guessed by extension or contents",
    callback=get_obsolete_callback_for_click(
        ".txt files are now read as plain text, .xml or .readalong as XML, and other files based on\n"
        "whether they start with <?xml or not."
    ),
)
@click.option(
    "--lang-no-append-und",
    is_flag=True,
    default=False,
    hidden=True,
    help="Hidden option to disable to automatic appending of und (Undetermined) to -l",
)
@click.option(
    "-oo",
    "--output-orth",
    default="eng-arpabet",
    hidden=True,
    help="Hidden option to change the output orthography",
)
@click.option(
    "-l",
    "--language",
    "--languages",
    multiple=True,
    callback=JoinerCallbackForClick(get_langs_deferred()),
    help=(
        "The language code(s) for text in TEXTFILE (use only with plain text input); "
        "multiple codes can be joined by ',' or ':', or by repeating the option, "
        "to enable the g2p cascade (run 'readalongs g2p -h' for details); "
        "run 'readalongs langs' to list all supported languages."
    ),
)
@click.option(
    "-m",
    "--align-mode",
    type=click.Choice(["strict", "moderate", "loose", "auto"], case_sensitive=False),
    help=(
        "Decoder search parameters: "
        "'strict' means a narrow beam, fastest but might fail to find an alignment; "
        "'loose' means an unlimited beam, slowest, should always succeed but the alignment is more likely to be wrong; "
        "'moderate' is in between; "
        "'auto' (the default) means try strict first, and fall back to moderate "
        "then loose if no alignment is found."
    ),
    default="auto",
)
@click.option(
    "-s",
    "--save-temps",
    is_flag=True,
    help="Save intermediate stages of processing and temporary files (dictionary, FSG, tokenization, etc)",
)
@click.option(
    "--g2p-fallback",
    hidden=True,
    default=None,
    help="OBSOLETE; enable the g2p cascade by giving -l with multiple langs instead",
    callback=get_obsolete_callback_for_click(
        "Specify multiple languages with the -l/--language option instead,\n"
        "or by adding the 'fallback-langs' attribute where relevant in your XML input."
    ),
)
@click.option("-d", "--debug", is_flag=True, help="Display debugging messages")
@click.option("--debug-aligner", is_flag=True, help="Display logs from the aligner")
@click.option(
    "--debug-g2p",
    is_flag=True,
    default=False,
    help="Display verbose g2p error messages",
)
@click.option(
    "--g2p-verbose",
    is_flag=True,
    hidden=True,
    default=None,
    help="OBSOLETE: now --debug-g2p",
    callback=get_obsolete_callback_for_click("Use --debug-g2p instead."),
)
def align(**kwargs):  # noqa: C901  # some versions of flake8 need this here instead
    """Align TEXTFILE and AUDIOFILE and create output files as OUTPUT_BASE.* in directory
    OUTPUT_BASE/.

    TEXTFILE:    Input text file path (in XML or plain text)

    \b
    If TEXTFILE has a .xml or .readalong extension or starts with an XML declaration line,
    it is parsed as XML and can be in one of three formats:
     - the output of 'readalongs make-xml',
     - the output of 'readalongs tokenize', or
     - the output of 'readalongs g2p'.

    \b
    If TEXTFILE has a .txt extension or does not start with an XML declaration
    line, it is read as plain text with the following conventions:
     - The text should be plain UTF-8 text without any markup.
     - Paragraph breaks are indicated by inserting one blank line.
     - Page breaks are indicated by inserting two blank lines.

    One can add the known ARPABET phonetics in the XML for words (<w> elements)
    that are not correctly handled by g2p in the output of 'readalongs tokenize'
    or 'readalongs g2p', via the ARPABET attribute.

    One can add anchor elements in the XML, e.g., '<anchor time="2.345s"/>', to
    mark known anchor points between the audio and text stream.

    AUDIOFILE:   Input audio file path, in any format supported by ffmpeg

    OUTPUT_BASE: Output files will be saved as OUTPUT_BASE/OUTPUT_BASE.*
    """
    # deferred expensive imports
    import json
    from tempfile import TemporaryFile

    from lxml import etree

    from readalongs.align import align_audio, create_input_ras, save_readalong
    from readalongs.log import LOGGER
    from readalongs.text.util import load_xml

    config_file = kwargs.get("config", None)
    config = None
    if config_file:
        if str(config_file).endswith("json"):
            try:
                with open(config_file, encoding="utf-8-sig") as f:
                    config = json.load(f)
            except json.decoder.JSONDecodeError as e:
                raise click.BadParameter(
                    f"Config file at {config_file} is not in valid JSON format: {e}."
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

    # Determine if the file is plain text or XML
    textfile_name = kwargs["textfile"]
    if str(textfile_name).endswith(".xml"):
        textfile_is_plaintext = False  # .xml is XML
    elif str(textfile_name).endswith(".readalong"):
        textfile_is_plaintext = False  # .readalong is XML
    elif str(textfile_name).endswith(".txt"):
        textfile_is_plaintext = True  # .txt is plain text
    else:
        # Files other than .xml or .txt are parsed using etree. If the parse is
        # successful or the first syntax error is past the first line, the file
        # is assumed to be XML. Plain text files will yield an error in the
        # first few characters of line 1, typically complaining about not
        # finding "<" at the start.
        # There are many valid "magic numbers" for XML files, depending on
        # their encoding (utf8, utf16, endianness, etc). If we looked for
        # "<?xml " at the beginning, that would only catch some of the valid
        # XML encodings that etree can parse.
        # We could also use python-magic or filetype, but why introduce another
        # dependency when we can ask the library we're already using!?
        try:
            _ = load_xml(textfile_name)
        except etree.ParseError as e:
            textfile_is_plaintext = e.position <= (1, 10)
        else:
            textfile_is_plaintext = False

    if textfile_is_plaintext:
        if not kwargs["language"]:
            raise click.BadParameter(
                "No input language specified for plain text input. "
                "Please provide the -l/--language switch."
            )
        languages = list(kwargs["language"])
        if not kwargs["lang_no_append_und"] and "und" not in languages:
            languages.append("und")
        plain_textfile = kwargs["textfile"]
        try:
            _, xml_textfile = create_input_ras(
                input_file_name=plain_textfile,
                text_languages=languages,
                save_temps=temp_base,
            )
        except (RuntimeError, OSError) as e:
            raise click.UsageError(e) from e
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
            verbose_g2p_warnings=kwargs["debug_g2p"],
            debug_aligner=kwargs["debug_aligner"],
            output_orthography=kwargs["output_orth"],
            alignment_mode=kwargs["align_mode"],
        )
    except RuntimeError as e:
        raise click.UsageError(e) from e
        # LOGGER.error(e)
        # sys.exit(1)

    output_formats = kwargs["output_formats"]

    save_readalong(
        align_results=results,
        output_dir=output_dir,
        output_basename=output_basename,
        config=config,
        audiofile=kwargs["audiofile"],
        audiosegment=results["audio"],
        output_formats=output_formats,
    )


@cli.command(  # type: ignore  # quench spurious mypy error: "Command" has no attribute "command"
    context_settings=CONTEXT_SETTINGS,
    short_help="Renamed: use 'readalongs make-xml' instead.",
    deprecated=True,
)
@click.argument("plaintextfile", type=click.File("r", encoding="utf-8-sig", lazy=True))
@click.argument("xmlfile", type=click.Path(), required=False, default="")
@click.option("-d", "--debug", is_flag=True, help="Add debugging messages to logger")
@click.option(
    "-f", "--force-overwrite", is_flag=True, help="Force overwrite output files"
)
@click.option(
    "--lang-no-append-und",
    is_flag=True,
    default=False,
    hidden=True,
    help="Hidden option to disable to automatic appending of und (Undetermined) to -l",
)
@click.option(
    "-l",
    "--language",
    "--languages",
    required=True,
    multiple=True,
    callback=JoinerCallbackForClick(get_langs_deferred()),
    help=(
        "The language code(s) for text in PLAINTEXTFILE; "
        "multiple codes can be joined by ',' or ':', or by repeating the option, "
        "to enable the g2p cascade (run 'readalongs g2p -h' for details); "
        "run 'readalongs langs' to list all supported languages."
    ),
)
def prepare(**kwargs):
    """DEPRECATED - renamed: use `readalongs make-xml` instead.

    make XMLFILE for 'readalongs align' from PLAINTEXTFILE.

    PLAINTEXTFILE must be plain text encoded in UTF-8, with one sentence per line,
    paragraph breaks marked by a blank line, and page breaks marked by two
    blank lines.

    PLAINTEXTFILE: Path to the plain text input file, or - for stdin

    XMLFILE:       Path to the XML output file, or - for stdout [default: PLAINTEXTFILE.readalong]
    """
    from readalongs.log import LOGGER

    LOGGER.warning(
        'WARNING: "readalongs prepare" is deprecated. Use "readalongs make-xml" instead.'
    )
    make_xml.callback(**kwargs)


@cli.command(  # type: ignore  # quench spurious mypy error: "Command" has no attribute "command"
    context_settings=CONTEXT_SETTINGS,
    short_help="Convert a plain text file into the XML format for alignment.",
)
@click.argument("plaintextfile", type=click.File("r", encoding="utf-8-sig", lazy=True))
@click.argument("xmlfile", type=click.Path(), required=False, default="")
@click.option("-d", "--debug", is_flag=True, help="Add debugging messages to logger")
@click.option(
    "-f", "--force-overwrite", is_flag=True, help="Force overwrite output files"
)
@click.option(
    "--lang-no-append-und",
    is_flag=True,
    default=False,
    hidden=True,
    help="Hidden option to disable to automatic appending of und (Undetermined) to -l",
)
@click.option(
    "-l",
    "--language",
    "--languages",
    required=True,
    multiple=True,
    callback=JoinerCallbackForClick(get_langs_deferred()),
    help=(
        "The language code(s) for text in PLAINTEXTFILE; "
        "multiple codes can be joined by ',' or ':', or by repeating the option, "
        "to enable the g2p cascade (run 'readalongs g2p -h' for details); "
        "run 'readalongs langs' to list all supported languages."
    ),
)
def make_xml(**kwargs):
    """make XMLFILE for 'readalongs align' from PLAINTEXTFILE.

    PLAINTEXTFILE must be plain text encoded in UTF-8, with one sentence per line,
    paragraph breaks marked by a blank line, and page breaks marked by two
    blank lines.

    PLAINTEXTFILE: Path to the plain text input file, or - for stdin

    XMLFILE:       Path to the XML output file, or - for stdout [default: PLAINTEXTFILE.readalong]
    """
    # deferred expensive import
    from readalongs.align import create_input_ras
    from readalongs.log import LOGGER

    if kwargs["debug"]:
        LOGGER.setLevel("DEBUG")
        LOGGER.info(
            "Running readalongs make-xml(lang={}, force-overwrite={}, plaintextfile={}, xmlfile={}).".format(
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
            base, ext = os.path.splitext(out_file)
            if ext == ".txt":
                out_file = base
            out_file += ".readalong"

    languages = list(kwargs["language"])
    if not kwargs["lang_no_append_und"] and "und" not in languages:
        languages.append("und")

    try:
        if out_file == "-":
            _, filename = create_input_ras(
                input_file_handle=input_file, text_languages=languages
            )
            with io.open(filename, encoding="utf-8-sig") as f:
                sys.stdout.write(f.read())
        else:
            if not str(out_file).endswith(".readalong"):
                out_file += ".readalong"
            if os.path.exists(out_file) and not kwargs["force_overwrite"]:
                raise click.BadParameter(
                    "Output file %s exists already, use -f to overwrite." % out_file
                )

            _, filename = create_input_ras(
                input_file_handle=input_file,
                text_languages=languages,
                output_file=out_file,
            )
    except (RuntimeError, OSError) as e:
        raise click.UsageError(e) from e

    LOGGER.info("Wrote {}".format(out_file))


@cli.command(  # type: ignore  # quench spurious mypy error: "Command" has no attribute "command"
    context_settings=CONTEXT_SETTINGS,
    short_help="Tokenize an XML file, in preparation for alignment.",
)
@click.argument("xmlfile", type=click.File("rb"))
@click.argument("tokfile", type=click.Path(), required=False, default="")
@click.option("-d", "--debug", is_flag=True, help="Add debugging messages to logger")
@click.option(
    "-f", "--force-overwrite", is_flag=True, help="Force overwrite output files"
)
def tokenize(**kwargs):
    """Tokenize XMLFILE for 'readalongs align' into TOKFILE.

    XMLFILE should have been produced by 'readalongs make-xml'.
    TOKFILE can then be augmented with word-specific language codes.
    'readalongs align' can be called with either XMLFILE or TOKFILE as XML input.

    XMLFILE: Path to the XML file to tokenize, or - for stdin

    TOKFILE: Output path for the tok'd XML, or - for stdout [default: XMLFILE.tokenized.readalong]
    """
    from lxml import etree

    from readalongs.log import LOGGER
    from readalongs.text.tokenize_xml import tokenize_xml
    from readalongs.text.util import load_xml, save_xml, write_xml

    if kwargs["debug"]:
        LOGGER.setLevel("DEBUG")
        LOGGER.info(
            "Running readalongs tokenize(xmlfile={}, tokfile={}, force-overwrite={}).".format(
                kwargs["xmlfile"], kwargs["tokfile"], kwargs["force_overwrite"]
            )
        )

    input_file = kwargs["xmlfile"]

    if not kwargs["tokfile"]:
        output_path = get_click_file_name(input_file)
        if output_path != "-":
            base, ext = os.path.splitext(str(output_path))
            if ext == ".readalong":
                output_path = base
            output_path += ".tokenized.readalong"
    else:
        output_path = kwargs["tokfile"]
        base, ext = os.path.splitext(str(output_path))
        if ext != ".readalong" and output_path != "-":
            output_path += ".readalong"

    if os.path.exists(output_path) and not kwargs["force_overwrite"]:
        raise click.BadParameter(
            "Output file %s exists already, use -f to overwrite." % output_path
        )

    try:
        xml = load_xml(input_file)
    except etree.ParseError as e:
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


@cli.command(  # type: ignore  # quench spurious mypy error: "Command" has no attribute "command"
    context_settings=CONTEXT_SETTINGS,
    short_help="Apply g2p to a tokenized file, in preparation for alignment.",
)
@click.argument("tokfile", type=click.File("rb", lazy=True))
@click.argument("g2pfile", type=click.Path(), required=False, default="")
@click.option(
    "--g2p-fallback",
    hidden=True,
    default=None,
    help="OBSOLETE; enable the g2p cascade by giving -l with multiple langs to prepare instead",
    callback=get_obsolete_callback_for_click(
        "Specify multiple languages with the -l/--language option to prepare instead,\n"
        "or by adding the 'fallback-langs' attribute where relevant in your XML input."
    ),
)
@click.option(
    "-f", "--force-overwrite", is_flag=True, help="Force overwrite output files"
)
@click.option(
    "--debug-g2p",
    is_flag=True,
    default=False,
    help="Display verbose messages about g2p errors.",
)
@click.option("-d", "--debug", is_flag=True, help="Add debugging messages to logger")
@click.option(
    "--g2p-verbose",
    is_flag=True,
    hidden=True,
    default=None,
    help="OBSOLETE: now --debug-g2p",
    callback=get_obsolete_callback_for_click("Use --debug-g2p instead."),
)
def g2p(**kwargs):
    """Apply g2p mappings to TOKFILE into G2PFILE.

    TOKFILE should have been produced by 'readalongs tokenize'.
    G2PFILE can then be modified to adjust the phonetic representation as needed.
    'readalongs align' can be called with G2PFILE instead of TOKFILE as XML input.

    The g2p cascade will be enabled whenever an XML element or any of its
    ancestors in TOKFILE has the attribute "fallback-langs" containing a comma-
    or colon-separated list of language codes. Provide multiple language codes to
    "readalongs make-xml" via its -l option to generate this attribute globally,
    or add it manually where needed. Undetermined, "und", is automatically
    added at the end of the language list provided via -l.

    With the g2p cascade, if a word cannot be mapped to valid ARPABET with the
    language found in the "xml:lang" attribute, the languages in
    "fallback-langs" are tried in order until a valid ARPABET mapping is
    generated.

    The output XML file can be used as input to align.

    TOKFILE: Path to the input tokenized XML file, or - for stdin

    G2PFILE: Output path for the g2p'd XML, or - for stdout [default: TOKFILE
    with .g2p. inserted]
    """
    # Defer expensive imports
    from lxml import etree

    from readalongs.log import LOGGER
    from readalongs.text.add_ids_to_xml import add_ids
    from readalongs.text.convert_xml import convert_xml
    from readalongs.text.util import load_xml, save_xml, write_xml

    if kwargs["debug"]:
        LOGGER.setLevel("DEBUG")
        LOGGER.info(
            "Running readalongs g2p(tokfile={}, g2pfile={}, force-overwrite={}).".format(
                kwargs["tokfile"], kwargs["g2pfile"], kwargs["force_overwrite"]
            )
        )

    input_file = kwargs["tokfile"]

    if not kwargs["g2pfile"]:
        output_path = get_click_file_name(input_file)
        if output_path != "-":
            base, ext = os.path.splitext(output_path)
            if ext == ".readalong":
                output_path = base
            base, ext = os.path.splitext(output_path)
            if ext == ".tokenized":
                output_path = base
            output_path += ".g2p.readalong"
    else:
        output_path = kwargs["g2pfile"]
        base, ext = os.path.splitext(output_path)
        if ext != ".readalong" and output_path != "-":
            output_path += ".readalong"

    if os.path.exists(output_path) and not kwargs["force_overwrite"]:
        raise click.BadParameter(
            "Output file %s exists already, use -f to overwrite." % output_path
        )

    try:
        xml = load_xml(input_file)
    except etree.ParseError as e:
        raise click.BadParameter(
            "Error parsing input file %s as XML, please verify it. Parser error: %s"
            % (get_click_file_name(input_file), e)
        )

    # Add the IDs to paragraph, sentences, word, etc.
    xml = add_ids(xml)

    # Apply the g2p mappings.
    xml, valid = convert_xml(xml, verbose_warnings=kwargs["debug_g2p"])

    if output_path == "-":
        write_xml(sys.stdout.buffer, xml)
    else:
        save_xml(output_path, xml)
        LOGGER.info("Wrote {}".format(output_path))

    if not valid:
        LOGGER.error(
            "Some word(s) could not be g2p'd correctly."
            + (
                " Run again with --debug-g2p to get more detailed error messages."
                if not kwargs["debug_g2p"]
                else ""
            )
        )
        sys.exit(1)


@cli.command(  # type: ignore  # quench spurious mypy error: "Command" has no attribute "command"
    context_settings=CONTEXT_SETTINGS,
    short_help="List the languages supported by g2p for readalongs.",
)
def langs():
    """List all the language codes and names currently supported by g2p
    that can be used for ReadAlongs creation.
    """
    _, langs_dict = get_langs()
    for code, name in langs_dict.items():
        print("%-8s\t%s" % (code, name))
