import os
import click
import wave
import shutil
from flask.cli import FlaskGroup
from readalongs._version import __version__
from readalongs.app import app
from readalongs.lang import get_langs
from readalongs.align import align_audio
from readalongs.log import LOGGER
from readalongs.g2p.make_smil import make_smil
from readalongs.g2p.util import save_xml, save_txt
from readalongs.align import create_input_xml, convert_to_xhtml, write_to_text_grid

LANGS = [x['code'] for x in get_langs()]


def create_app():
    return app


@click.version_option(version=__version__, prog_name="ReadAlong CLI")
@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """Management script for Read Along Studio."""


@app.cli.command()
@click.argument('inputfile', type=click.Path(exists=True, readable=True))
@click.argument('wavfile', type=click.Path(exists=True, readable=True))
@click.argument('output-base', type=click.STRING)
@click.option('-d', '--debug', is_flag=True, help='Add debugging messages to logger')
@click.option('-f', '--force-overwrite', is_flag=True, help='Force overwrite output files')
@click.option('-i', '--text-input', is_flag=True, help='Input is plain text (assume paragraphs separated by blank lines)')
@click.option('-l', '--language', type=click.Choice(LANGS, case_sensitive=False), help='Set language for plain text input')
@click.option('-s', '--save-temps', is_flag=True,
              help='Save intermediate stages of processing and temporary files (dictionary, FSG, tokenization etc)')
@click.option('-t', '--text-grid', is_flag=True, help='Export to Praat TextGrid & ELAN eaf file')
@click.option('-x', '--output-xhtml', is_flag=True, help='Output simple XHTML instead of XML')
def align(**kwargs):
    """
    Align INPUTFILE and WAVFILE and create output files at OUTPUT.

    INPUTFILE is the input XML or text file

    WAVFILE is the input audio file

    OUTPUT_BASE is the basename for output files
    """
    if kwargs['debug']:
        LOGGER.setLevel('DEBUG')
    if kwargs['text_input']:
        tempfile, kwargs.inputfile \
            = create_input_xml(kwargs['inputfile'],
                               text_language=kwargs['text_language'],
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
        textgrid = write_to_text_grid(results, duration)
        textgrid.to_file(kwargs['output_base'] + '.TextGrid')
        textgrid.to_eaf().to_file(kwargs['output_base'] + ".eaf")

    if kwargs['output_xhtml']:
        convert_to_xhtml(results['tokenized'])

    save_xml(tokenized_xml_path, results['tokenized'])
    smil = make_smil(os.path.basename(tokenized_xml_path),
                     os.path.basename(wav_path), results)
    shutil.copy(kwargs['wavfile'], wav_path)
    save_txt(smil_path, smil)
