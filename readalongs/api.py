"""
api.py: API for calling readalongs CLI commands programmatically

In this API, functions take the same arguments as on the readalongs
command-line interface. The mapping between CLI options and API options is
that the first long variant of an option described in "readalongs <cmd> -h" is
the API option name, with hyphens replaced by undercores.

Example from readalongs align -h:
    option in CLI                       option in API
    ================================    =================================
    -l, --language, --languages TEXT    language=["l1", "l2"]
    -f, --force-overwrite               force_overwrite=True
    -c, --config PATH                   config=os.path.join("some", "path", "config.json")
                                     OR config=pathlib.Path("/some/path/config.json")

As shown above, file names can be constructed using os.path.join() or a Path
class like pathlib.Path. Warning: don't just use "/some/path/config.json"
because that is not portable accross platforms.

Options that can be specified multiple times on the CLI should be provided as a
list to the API methods.

All API functions return the following tuple: (status, exception, log)
 - status: 0 for OK, non-0 for Error
 - exception: any exception caught, one of:
    - click.BadParameter: when the is an error with the combination of parameters given
    - click.UsageError: when the alignment task requested cannot be completed
    - other exceptions: something else unexpected went wrong. Please report this as
                        a bug at https://github.com/ReadAlongs/Studio/issues if
                        you come accross such an exception and you believe the
                        problem is not in your own code.
 - log: any logging messages issued during execution

Additional API function:

convert_to_readalong(sentences: Sequence[Sequence[Token]], language: Sequence[str]) -> str:
    convert a list of sentences into a readalong XML string ready to print to file.
    Just like align and make_xml, this function expects a black line (empty list) to
    make a paragraph break, and two consecutive blank lines to make a page break.
    Unlike the other functions here, this function is not a wrapper around the CLI and
    it just returns the string, non status.
"""

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple, Union

import click

from readalongs import cli
from readalongs.align import create_ras_from_text
from readalongs.log import LOGGER
from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.util import parse_xml
from readalongs.util import JoinerCallbackForClick, get_langs_deferred


def align(
    textfile: Union[str, Path],
    audiofile: Union[str, Path],
    output_base: Union[str, Path],
    language: Sequence[str] = (),
    output_formats: Sequence[str] = (),
    **kwargs
) -> Tuple[int, Optional[Exception], str]:
    """Run the "readalongs align" command from within a Python script.

    Args:
        textfile: input text file (XML or plain text)
        audiofile: input audio file (format supported by ffmpeg)
        output_base: basename for output files
        language: Specify only if textfile is plain text;
            list of languages for g2p and g2p cascade
        save_temps (bool): Optional; whether to save temporary files

        Run "readalongs align -h" or consult
        https://readalong-studio.readthedocs.io/en/latest/cli-ref.html#readalongs-align
        for the full list of arguments and their meaning.

    Returns: (status, exception, log_text)
    """

    logging_stream = io.StringIO()
    logging_handler = logging.StreamHandler(logging_stream)
    try:
        # Capture the logs
        LOGGER.addHandler(logging_handler)

        align_args = {param.name: param.default for param in cli.align.params}
        if language:
            language = JoinerCallbackForClick(get_langs_deferred())(
                value_groups=language
            )
        if output_formats:
            output_formats = JoinerCallbackForClick(
                cli.SUPPORTED_OUTPUT_FORMATS, drop_case=True
            )(value_groups=output_formats)

        align_args.update(
            textfile=textfile,
            audiofile=audiofile,
            output_base=output_base,
            language=language,
            output_formats=output_formats,
            **kwargs,
        )

        cli.align.callback(**align_args)  # type: ignore

        return (0, None, logging_stream.getvalue())
    except Exception as e:
        return (1, e, logging_stream.getvalue())
    finally:
        # Remove the log-capturing handler
        LOGGER.removeHandler(logging_handler)


def make_xml(
    plaintextfile: Union[str, Path],
    xmlfile: Union[str, Path],
    language: Sequence[str],
    **kwargs
) -> Tuple[int, Optional[Exception], str]:
    """Run the "readalongs make-xml" command from within a Python script.

    Args:
        plaintextfile: input plain text file
        xmlfile: output XML file
        language: list of languages for g2p and g2p cascade

        Run "readalongs make-xml -h" or consult
        https://readalong-studio.readthedocs.io/en/latest/cli-ref.html#readalongs-make-xml
        for the full list of arguments and their meaning.

    Returns: (status, exception, log_text)
    """
    # plaintextfile is not a file object if passed from click

    plaintextfile = (
        plaintextfile.name
        if isinstance(plaintextfile, click.utils.LazyFile)
        else plaintextfile
    )
    xmlfile = str(xmlfile) if isinstance(xmlfile, Path) else xmlfile
    logging_stream = io.StringIO()
    logging_handler = logging.StreamHandler(logging_stream)
    try:
        # Capture the logs
        LOGGER.addHandler(logging_handler)

        make_xml_args = {param.name: param.default for param in cli.make_xml.params}
        try:
            with open(plaintextfile, "r", encoding="utf-8-sig") as plaintextfile_handle:
                make_xml_args.update(
                    plaintextfile=plaintextfile_handle,
                    xmlfile=xmlfile,
                    language=JoinerCallbackForClick(get_langs_deferred())(
                        value_groups=language
                    ),
                    **kwargs,
                )
                cli.make_xml.callback(**make_xml_args)  # type: ignore
        except OSError as e:
            # e.g.: FileNotFoundError or PermissionError on open(plaintextfile) above
            raise click.UsageError(str(e)) from e

        return (0, None, logging_stream.getvalue())
    except Exception as e:
        return (1, e, logging_stream.getvalue())
    finally:
        # Remove the log-capturing handler
        LOGGER.removeHandler(logging_handler)


def prepare(*args, **kwargs):
    """Deprecated, use make_xml instead"""
    LOGGER.warning(
        "readalongs.api.prepare() is deprecated. Please use make_xml() instead."
    )
    return make_xml(*args, **kwargs)


@dataclass
class Token:
    """A token in a readalong: a word has a time and dur, a non-word does not."""

    text: str
    time: Optional[float]
    dur: Optional[float]
    is_word: bool

    def __init__(
        self,
        text: str,
        time: Optional[float] = None,
        dur: Optional[float] = None,
        is_word: Optional[bool] = None,
    ):
        """Create a word token:
            t = Token("asdf", time=1.3, dur=.34) or t = Token("asdf", 1.3, .34)
        Create a non-word token (e.g., punctuation, spacing):
            t = Token(", ")
        """
        self.text = text
        self.time = time
        self.dur = dur
        self.is_word = is_word if is_word is not None else bool(time is not None)


def convert_to_readalong(
    sentences: Sequence[Sequence[Token]],
    language: Sequence[str] = ("und",),
) -> str:
    """Convert a list of sentences/paragraphs/pages of tokens into a readalong XML string.

    Args:
        sentences: a list of sentences, each of which is a list of Token objects
            Paragraph breaks are marked by a empty sentence (i.e., an empty list)
            Page breaks are marked by two empty sentences in a row
        language: list of languages to declare at the top of the readalong
            (has no functional effect since g2p is not applied, it's only metadata)

    Returns:
        str: the readalong XML string, ready to print to a .readalong file
    """
    from lxml import etree

    xml_text = create_ras_from_text(
        ["".join(token.text for token in sentence) for sentence in sentences],
        language,
    )
    xml = parse_xml(xml_text)
    filtered_sentences = [sentence for sentence in sentences if sentence]
    for sentence, sentence_xml in zip(filtered_sentences, xml.findall(".//s")):
        sentence_xml.text = ""
        for token in sentence:
            if token.is_word:
                w = etree.Element("w")
                w.text = token.text
                w.attrib["time"] = str(token.time)
                w.attrib["dur"] = str(token.dur)
                sentence_xml.append(w)
            else:
                if len(sentence_xml):  # if it has children
                    if not sentence_xml[-1].tail:
                        sentence_xml[-1].tail = ""
                    sentence_xml[-1].tail += token.text
                else:
                    sentence_xml.text += token.text

    xml = add_ids(xml)
    xml_text = etree.tostring(
        xml,
        encoding="utf-8",
        xml_declaration=True,
    ).decode("utf8")

    return xml_text + "\n"
