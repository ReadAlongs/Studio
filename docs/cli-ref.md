(cli-ref)=

# Command line interface (CLI) reference

This page contains the full reference documentation for each command in the CLI.
See also {ref}`cli-guide` for guidelines on using the CLI.

The ReadAlongs CLI has five key commands:

- {ref}`cli-align`: full alignment pipeline, from plain text or XML to a
  viewable readalong
- {ref}`cli-make-xml`: convert a plain text file into XML, for align
- {ref}`cli-tokenize`: tokenize an XML file
- {ref}`cli-g2p`: g2p a tokenized XML file
- {ref}`cli-langs`: list supported languages

Each command can be run with `-h` or `--help` to display its usage manual,
e.g., `readalongs -h`, `readalongs align --help`.

(cli-align)=

```{eval-rst}
.. click:: readalongs.cli:align
  :prog: readalongs align
```

(cli-make-xml)=

```{eval-rst}
.. click:: readalongs.cli:make_xml
  :prog: readalongs make-xml
```

(cli-tokenize)=

```{eval-rst}
.. click:: readalongs.cli:tokenize
  :prog: readalongs tokenize
```

(cli-g2p)=

```{eval-rst}
.. click:: readalongs.cli:g2p
  :prog: readalongs g2p
```

(cli-langs)=

```{eval-rst}
.. click:: readalongs.cli:langs
  :prog: readalongs langs
```
