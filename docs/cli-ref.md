# Command line interface (CLI) reference

This page contains the full reference documentation for each command in the CLI.
See also [Command line interface (CLI) user guide](cli-guide.md) for guidelines on using the CLI.

The ReadAlongs CLI has five key commands:

- [`readalongs align`][readalongs-align]: full alignment pipeline, from plain text or XML to a
  viewable readalong
- [`readalongs make-xml`][readalongs-make-xml]: convert a plain text file into XML, for align
- [`readalongs tokenize`][readalongs-tokenize]: tokenize an XML file
- [`readalongs g2p`][readalongs-g2p]: g2p a tokenized XML file
- [`readalongs langs`][readalongs-langs]: list supported languages

Each command can be run with `-h` or `--help` to display its usage manual,
e.g., `readalongs -h`, `readalongs align --help`.

::: mkdocs-click
    :module: readalongs.cli
    :command: align
    :prog_name: readalongs align

::: mkdocs-click
    :module: readalongs.cli
    :command: make_xml
    :prog_name: readalongs make-xml

::: mkdocs-click
    :module: readalongs.cli
    :command: tokenize
    :prog_name: readalongs tokenize

::: mkdocs-click
    :module: readalongs.cli
    :command: g2p
    :prog_name: readalongs g2p

::: mkdocs-click
    :module: readalongs.cli
    :command: langs
    :prog_name: readalongs langs
