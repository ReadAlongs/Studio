#!/bin/sh

# Must be a better way to find this!
PSDIR=$(dirname $(which sphinx_fe))/../share/pocketsphinx
sphinx_fe -c fileids -mswav yes -remove_noise no -remove_silence no -ei wav -eo mfc \
	  -argfile $PSDIR/model/en-us/en-us/feat.params
