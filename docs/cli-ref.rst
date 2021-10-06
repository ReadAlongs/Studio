.. _cli-ref:

Command line interface (CLI) reference
======================================

This page contains the full reference documentation for each command in the CLI.
See also :ref:`cli-guide` for guidelines on using the CLI.

The ReadAlongs CLI has four key commands:

- :ref:`cli-align`: full alignment pipeline, from plain text or XML to a
  viewable readalong
- :ref:`cli-prepare`: convert a plain text file into XML, for align
- :ref:`cli-tokenize`: tokenize a prepared XML file
- :ref:`cli-g2p`: g2p a tokenized XML file

Each command can be run with ``-h`` or ``--help`` to display its usage manual,
e.g., ``readalongs -h``, ``readalongs align --help``.

.. _cli-align:
.. click:: readalongs.cli:align
  :prog: readalongs align

.. _cli-prepare:
.. click:: readalongs.cli:prepare
  :prog: readalongs prepare

.. _cli-tokenize:
.. click:: readalongs.cli:tokenize
  :prog: readalongs tokenize

.. _cli-g2p:
.. click:: readalongs.cli:g2p
  :prog: readalongs g2p
