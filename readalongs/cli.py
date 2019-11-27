#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# cli.py
#
#   Initializes a Command Line Interface with Click.
#   The main purpose of the cli is to align input files.
#
#######################################################################

import os
import wave
import shutil


import click
from networkx import has_path
from flask.cli import FlaskGroup
from g2p.mappings.langs import LANGS_AVAILABLE, LANGS_NETWORK

from readalongs.app import app
from readalongs.log import LOGGER
from readalongs.align import align_audio
from readalongs._version import __version__
from readalongs.text.make_smil import make_smil
from readalongs.text.util import save_xml, save_txt
from readalongs.epub.create_epub import create_epub
from readalongs.align import write_to_subtitles, write_to_text_grid
from readalongs.align import create_input_tei, convert_to_xhtml, return_words_and_sentences


# get the key from all networks in text module that have a path to 'eng-arpabet'
# which is needed for the readalongs
LANGS = [k for x in LANGS_AVAILABLE for k in x.keys() if LANGS_NETWORK.has_node(
    k) and has_path(LANGS_NETWORK, k, 'eng-arpabet')]

# Hack to allow old English LexiconG2P
LANGS += ['eng']


def create_app():
    ''' Returns the app
    '''
    return app


@click.version_option(version=__version__, prog_name="readalongs")
@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """Management script for Read Along Studio."""


@app.cli.command()
@click.argument('inputfile', type=click.Path(exists=True, readable=True))
@click.argument('wavfile', type=click.Path(exists=True, readable=True))
@click.argument('output-base', type=click.STRING)
@click.option('-c', '--closed-captioning', is_flag=True, help='Export sentences to WebVTT and SRT files')
@click.option('-d', '--debug', is_flag=True, help='Add debugging messages to logger')
@click.option('-f', '--force-overwrite', is_flag=True, help='Force overwrite output files')
@click.option('-i', '--text-input', is_flag=True, help='Input is plain text (assume paragraphs separated by blank lines)')
@click.option('-l', '--language', type=click.Choice(LANGS, case_sensitive=False), help='Set language for plain text input')
@click.option('-s', '--save-temps', is_flag=True,
              help='Save intermediate stages of processing and temporary files (dictionary, FSG, tokenization etc)')
@click.option('-t', '--text-grid', is_flag=True, help='Export to Praat TextGrid & ELAN eaf file')
@click.option('-x', '--output-xhtml', is_flag=True, help='Output simple XHTML instead of XML')
def align(**kwargs):
    """Align INPUTFILE and WAVFILE and create output files at OUTPUT_BASE.
    
    inputfile : A path to the input text file

    wavfile : A path to the input audio file

    output-base : A base name for output files
    """
    if kwargs['debug']:
        LOGGER.setLevel('DEBUG')
    if kwargs['text_input']:
        tempfile, kwargs['inputfile'] \
            = create_input_tei(kwargs['inputfile'],
                               text_language=kwargs['language'],
                               save_temps=(kwargs['output_base']
                                           if kwargs['save_temps'] else None))
    if kwargs['output_xhtml']:
        tokenized_xml_path = '%s.xhtml' % kwargs['output_base']
    else:
        _, input_ext = os.path.splitext(kwargs['inputfile'])
        tokenized_xml_path = '%s%s' % (kwargs['output_base'], input_ext)
    if os.path.exists(tokenized_xml_path) and not kwargs['force_overwrite']:
        raise click.BadParameter("Output file %s exists already, did you mean to do that?"
                                 % tokenized_xml_path)
    smil_path = kwargs['output_base'] + '.smil'
    if os.path.exists(smil_path) and not kwargs['force_overwrite']:
        raise click.BadParameter("Output file %s exists already, did you mean to do that?"
                                 % smil_path)
    _, wav_ext = os.path.splitext(kwargs['wavfile'])
    wav_path = kwargs['output_base'] + wav_ext
    if os.path.exists(wav_path) and not kwargs['force_overwrite']:
        raise click.BadParameter("Output file %s exists already, did you mean to do that?"
                                 % wav_path)

    try:
        results = align_audio(kwargs['inputfile'], kwargs['wavfile'],
                              save_temps=(kwargs['output_base']
                                          if kwargs['save_temps'] else None))
    except RuntimeError as e:
        LOGGER.error(e)
        exit(1)

    if kwargs['text_grid']:
        with wave.open(kwargs['wavfile'], 'r') as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)
        words, sentences = return_words_and_sentences(results)
        textgrid = write_to_text_grid(words, sentences, duration)
        textgrid.to_file(kwargs['output_base'] + '.TextGrid')
        textgrid.to_eaf().to_file(kwargs['output_base'] + ".eaf")

    if kwargs['closed_captioning']:
        words, sentences = return_words_and_sentences(results)
        webvtt_sentences = write_to_subtitles(sentences)
        webvtt_sentences.save(kwargs['output_base'] + '_sentences.vtt')
        webvtt_sentences.save_as_srt(kwargs['output_base'] + '_sentences.srt')
        webvtt_words = write_to_subtitles(words)
        webvtt_words.save(kwargs['output_base'] + '_words.vtt')
        webvtt_words.save_as_srt(kwargs['output_base'] + '_words.srt')

    if kwargs['output_xhtml']:
        convert_to_xhtml(results['tokenized'])

    save_xml(tokenized_xml_path, results['tokenized'])
    smil = make_smil(os.path.basename(tokenized_xml_path),
                     os.path.basename(wav_path), results)
    shutil.copy(kwargs['wavfile'], wav_path)
    save_txt(smil_path, smil)


@app.cli.command()
@click.argument('input', type=click.Path(exists=True, readable=True))
@click.argument('output', type=click.Path(exists=False, readable=True))
@click.option('-u', '--unpacked', is_flag=True, help='Output unpacked directory of files (for testing)')
def epub(**kwargs):
    """
    Convert INPUT smil document to epub with media overlay at OUTPUT

    input : the .smil document

    output : the path to the .epub output
    """
    create_epub(kwargs['input'], kwargs['output'], kwargs['unpacked'])
