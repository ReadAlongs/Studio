"""
api.py: API for calling readalongs CLI commands programmatically
"""

from readalongs import cli


def align(textfile, audiofile, output_base, language=None, **kwargs):
    """Run the "readalongs align" command from within a Python script.

    Args:
        textfile (str): input text file (XML or plain text)
        audiofile (str): input audio file (format supported by ffmpeg)
        output_base (str): basename for output files
        language (list[str]): Specify only of textfile is plain text;
            list of languages for g2p and g2p cascade
        save_temps (bool): Optional; whether to save temporary files

    Run "readalongs align -h" or consult
    https://readalong-studio.readthedocs.io/en/latest/cli-ref.html#readalongs-align
    for the full list of arguments and their meaning. The name of an argument
    here is the first long name of each argument there, with hyphens replaced
    by underscores. All arguments not explicitly mentioned above are optional.

    Raises:
        click.BadParameter: when the is an error with the combination of parameters given
        click.UsageError: when the alignment task requested cannot be completed
    """

    align_args = {param.name: param.default for param in cli.align.params}
    align_args.update(
        textfile=textfile,
        audiofile=audiofile,
        output_base=output_base,
        language=language,
        **kwargs
    )
    if align_args["output_formats"] is None:
        align_args["output_formats"] = ()
    cli.align.callback(**align_args)
