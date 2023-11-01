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
"""

import io
import logging
from typing import Optional, Tuple

import click

from readalongs import cli
from readalongs.log import LOGGER
from readalongs.util import JoinerCallbackForClick, get_langs_deferred


def align(
    textfile, audiofile, output_base, language=(), output_formats=(), **kwargs
) -> Tuple[int, Optional[Exception], str]:
    """Run the "readalongs align" command from within a Python script.

    Args:
        textfile (str | Path): input text file (XML or plain text)
        audiofile (str | Path): input audio file (format supported by ffmpeg)
        output_base (str | Path): basename for output files
        language (List[str]): Specify only of textfile is plain text;
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
    plaintextfile, xmlfile, language, **kwargs
) -> Tuple[int, Optional[Exception], str]:
    """Run the "readalongs make-xml" command from within a Python script.

    Args:
        plaintextfile (str | Path): input plain text file
        xmlfile (str | Path): output XML file
        language (List[str]): list of languages for g2p and g2p cascade

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
