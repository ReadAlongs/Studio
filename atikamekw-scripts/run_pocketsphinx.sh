#!/bin/sh

pocketsphinx_batch -ctl fileids -fsgctl fileids -fsgext .fsg -cepdir . -dict ps_arpabet.dict -hypseg hypseg -backtrace yes -pbeam 1e-80 -wbeam 1e-80 -beam 1e-80
