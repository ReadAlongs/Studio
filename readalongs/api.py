"""
api.py: API for calling readalongs CLI commands programmatically

In this API, functions take the same arguments as on the readalongs
command-line interface. The mapping between CLI options and API options is
that the first long variant of an option described in "readalongs cmd -h" is
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

All API functions might raise the following exceptions:
    click.BadParameter: when the is an error with the combination of parameters given
    click.UsageError: when the alignment task requested cannot be completed
    other exceptions: something else unexpected went wrong. Please report this as
                      a bug at https://github.com/ReadAlongs/Studio/issues if
                      you come accross such an exception and you believe the
                      problem is not in your own code.
"""

import click
from readalongs import cli
from readalongs.util import JoinerCallbackForClick, get_langs_deferred


def align(textfile, audiofile, output_base, language=(), output_formats=(), **kwargs):
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

    Raises:
        click.BadParameter: when the is an error with the combination of parameters given
        click.UsageError: when the alignment task requested cannot be completed
    """

    align_args = {param.name: param.default for param in cli.align.params}
    if language:
        language = JoinerCallbackForClick(get_langs_deferred())(value_groups=language)
    if output_formats:
        output_formats = JoinerCallbackForClick(cli.SUPPORTED_OUTPUT_FORMATS)(
            value_groups=output_formats
        )

    align_args.update(
        textfile=textfile,
        audiofile=audiofile,
        output_base=output_base,
        language=language,
        output_formats=output_formats,
        **kwargs
    )

    cli.align.callback(**align_args)


def prepare(plaintextfile, xmlfile, language, **kwargs):
    """Run the "readalongs prepare" command from withint a Python script.

    Args:
        plaintextfile (str | Path): input plain text file
        xmlfile (str | Path): output XML file
        language (List[str]): list of languages for g2p and g2p cascade

        Run "readalongs prepare -h" or consult
        https://readalong-studio.readthedocs.io/en/latest/cli-ref.html#readalongs-prepare
        for the full list of arguments and their meaning.

    Raises:
        click.BadParameter: when the is an error with the combination of parameters given
        click.UsageError: when the alignment task requested cannot be completed
    """

    prepare_args = {param.name: param.default for param in cli.prepare.params}
    try:
        with open(plaintextfile, "r", encoding="utf8") as plaintextfile_handle:
            prepare_args.update(
                plaintextfile=plaintextfile_handle,
                xmlfile=xmlfile,
                language=JoinerCallbackForClick(get_langs_deferred())(
                    value_groups=language
                ),
                **kwargs
            )
            cli.prepare.callback(**prepare_args)
    except OSError as e:
        # e.g.: FileNotFoundError or PermissionError on open(plaintextfile) above
        raise click.UsageError(e) from e
