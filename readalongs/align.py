'''
Alignment for audiobooks
'''
from typing import Dict, List
from datetime import timedelta
import pocketsphinx
import regex as re
import argparse
import pystache
import shutil
import wave
import os
import io


from lxml import etree
from tempfile import NamedTemporaryFile
from pympi.Praat import TextGrid
from webvtt import WebVTT, Caption

from readalongs.audio_utils import read_audio_from_file
from readalongs.g2p.tokenize_xml import tokenize_xml
from readalongs.g2p.add_ids_to_xml import add_ids
from readalongs.g2p.convert_xml import convert_xml
from readalongs.g2p.lang_id import add_lang_ids
from readalongs.g2p.make_fsg import make_fsg
from readalongs.g2p.make_dict import make_dict
from readalongs.g2p.make_smil import make_smil
from readalongs.g2p.util import save_xml, save_txt

from readalongs.log import LOGGER

from readalongs import mapping_dir

####
#
# Some distros (Python2, Python3 on Windows it seems) don't have the WAV
# reading methods being context managers; the following checks whether the
# necessary methods are present and if not, add thems.
#
# Based on http://web.mit.edu/jgross/Public/21M.065/sound.py 9-24-2017
####


def _trivial__enter__(self):
    return self


def _self_close__exit__(self, exc_type, exc_value, traceback):
    self.close()


if not hasattr(wave.Wave_read, "__exit__"):
    wave.Wave_read.__exit__ = _self_close__exit__
if not hasattr(wave.Wave_write, "__exit__"):
    wave.Wave_write.__exit__ = _self_close__exit__
if not hasattr(wave.Wave_read, "__enter__"):
    wave.Wave_read.__enter__ = _trivial__enter__
if not hasattr(wave.Wave_write, "__enter__"):
    wave.Wave_write.__enter__ = _trivial__enter__


def align_audio(xml_path, wav_path, unit='w', save_temps=None):
    """
    Align an XML input file to an audio file.

    Args:
      xml_path: Path to XML input file in TEI-like format
      wav_path: Path to audio input (WAV or MP3)
      unit: Element to create alignments for.
      save_temps: Basename for intermediate output files (or
        None if they won't be saved)
    """
    results = {"words": []}

    # First do G2P
    try:
        xml = etree.parse(xml_path).getroot()
    except etree.XMLSyntaxError as e:
        raise RuntimeError(
            "Error parsing XML input file %s: %s." % (xml_path, e))
    xml = add_lang_ids(xml, mapping_dir, unit="s")
    xml = tokenize_xml(xml)
    if save_temps:
        save_xml(save_temps + '.tokenized.xml', xml)
    results['tokenized'] = xml = add_ids(xml)
    if save_temps:
        save_xml(save_temps + '.ids.xml', xml)
    xml = convert_xml(xml)
    if save_temps:
        save_xml(save_temps + '.g2p.xml', xml)

    # Now generate dictionary and FSG
    dict_data = make_dict(xml, xml_path, unit=unit)
    if save_temps:
        dict_file = io.open(save_temps + '.dict', 'wb')
    else:
        dict_file = NamedTemporaryFile(prefix='readalongs_dict_', delete=False)
    dict_file.write(dict_data.encode('utf-8'))
    dict_file.flush()
    fsg_data = make_fsg(xml, xml_path, unit=unit)
    if save_temps:
        fsg_file = io.open(save_temps + '.fsg', 'wb')
    else:
        fsg_file = NamedTemporaryFile(prefix='readalongs_fsg_', delete=False)
    fsg_file.write(fsg_data.encode('utf-8'))
    fsg_file.flush()

    # Now do alignment
    cfg = pocketsphinx.Decoder.default_config()
    model_path = pocketsphinx.get_model_path()
    cfg.set_boolean('-remove_noise', False)
    cfg.set_boolean('-remove_silence', False)
    cfg.set_string('-hmm', os.path.join(model_path, 'en-us'))
    cfg.set_string('-dict', dict_file.name)
    cfg.set_string('-fsg', fsg_file.name)
    # cfg.set_string('-samprate', "no no")
    cfg.set_float('-beam', 1e-100)
    cfg.set_float('-wbeam', 1e-80)

    _, wav_ext = os.path.splitext(wav_path)
    if wav_ext == '.wav':
        with wave.open(wav_path) as wav:
            LOGGER.info("Read %s: %d frames (%f seconds) audio"
                        % (wav_path, wav.getnframes(), wav.getnframes()
                            / wav.getframerate()))
            raw_data = wav.readframes(wav.getnframes())
            # Downsampling is (probably) not necessary
            cfg.set_float('-samprate', wav.getframerate())
    else:
        audio = read_audio_from_file(wav_path)
        audio = audio.set_channels(1).set_sample_width(2)
        # Downsampling is (probably) not necessary
        cfg.set_float('-samprate', audio.frame_rate)
        raw_data = audio.raw_data

    frame_points = int(cfg.get_float('-samprate')
                       * cfg.get_float('-wlen'))
    fft_size = 1
    while fft_size < frame_points:
        fft_size = fft_size << 1
    cfg.set_int('-nfft', fft_size)
    ps = pocketsphinx.Decoder(cfg)
    frame_size = 1.0 / cfg.get_int('-frate')

    def frames_to_time(frames):
        return frames * frame_size
    ps.start_utt()
    ps.process_raw(raw_data, no_search=False, full_utt=True)
    ps.end_utt()

    if not ps.seg():
        raise RuntimeError("Alignment produced no segments, "
                           "please examine dictionary and input audio and text.")

    for seg in ps.seg():
        start = frames_to_time(seg.start_frame)
        end = frames_to_time(seg.end_frame + 1)
        if seg.word in ('<sil>', '[NOISE]'):
            continue
        else:
            results["words"].append({
                "id": seg.word,
                "start": start,
                "end": end
            })
        LOGGER.info("Segment: %s (%.3f : %.3f)",
                    seg.word, start, end)

    if len(results['words']) == 0:
        raise RuntimeError("Alignment produced only noise or silence segments, "
                           "please examine dictionary and input audio and text.")

    if len(results['words']) != len(results['tokenized'].xpath('//w')):
        raise RuntimeError("Alignment produced a different number of segments and tokens, "
                           "please examine dictionary and input audio and text.")

    final_end = end

    # Split adjoining silence/noise between words
    last_end = 0.0
    last_word = dict()
    for word in results['words']:
        silence = word['start'] - last_end
        midpoint = last_end + silence / 2
        if silence > 0:
            if last_word:
                last_word['end'] = midpoint
            word['start'] = midpoint
        last_word = word
        last_end = word['end']
    silence = final_end - last_end
    if silence > 0:
        if last_word is not None:
            last_word['end'] += silence / 2

    dict_file.close()
    os.unlink(dict_file.name)
    fsg_file.close()
    os.unlink(fsg_file.name)

    return results


def return_word_from_id(xml, el_id):
    ''' Given an XML document, return the innertext at id
    '''
    return xml.xpath('//*[@id="%s"]/text()' % el_id)[0]


def return_words_and_sentences(results):
    ''' Parse xml into word and sentence 'tier' data
    '''
    result_id_pattern = re.compile(
        r'''
        t(?P<table>\d*)            # Table
        b(?P<body>\d*)             # Body
        d(?P<div>\d*)              # Div ( Break )
        p(?P<par>\d*)              # Paragraph
        s(?P<sent>\d+)             # Sentence
        w(?P<word>\d+)             # Word
        ''', re.VERBOSE)

    all_els = results['words']
    xml = results['tokenized']
    sentences = []
    words = []
    all_words = []
    current_sent = 0
    for el in all_els:
        parsed = re.search(result_id_pattern, el['id'])
        sent_i = parsed.group('sent')
        if int(sent_i) is not current_sent:
            sentences.append(words)
            words = []
            current_sent += 1
        word = {
            "text": return_word_from_id(xml, el['id']),
            "start": el['start'],
            "end": el['end']
        }
        words.append(word)
        all_words.append(word)
    sentences.append(words)
    return all_words, sentences


def write_to_text_grid(words, sentences, duration):
    ''' Write results to Praat TextGrid. Because we are using pympi, we can also export to Elan EAF.
    '''
    tg = TextGrid(xmax=duration)
    sentence_tier = tg.add_tier(name='Sentence')
    word_tier = tg.add_tier(name='Word')
    for s in sentences:
        sentence_tier.add_interval(
            begin=s[0]['start'],
            end=s[-1]['end'],
            value=' '.join([w['text'] for w in s]))

    for w in words:
        word_tier.add_interval(
            begin=w['start'],
            end=w['end'],
            value=w['text'])

    return tg


def float_to_timedelta(n: float) -> str:
    td = timedelta(seconds=n)
    if not td.microseconds:
        return str(td) + ".000"
    return str(td)


def write_to_subtitles(data: List[dict]):
    '''Returns WebVTT object from data.
       Data must be either a 'word'-type tier with
       a list of dicts that have keys for 'start', 'end' and
       'text'. Or a 'sentence'-type tier with a list of lists of dicts.
       Function return_words_and_sentences returns the proper format.
    '''
    vtt = WebVTT()
    for caption in data:
        if isinstance(caption, list):
            formatted = Caption(float_to_timedelta(caption[0]['start']),
                                float_to_timedelta(caption[-1]['end']),
                                ' '.join([w['text'] for w in caption]))
        else:
            formatted = Caption(float_to_timedelta(caption['start']),
                                float_to_timedelta(caption['end']),
                                caption['text'])
        vtt.captions.append(formatted)
    return vtt


def convert_to_xhtml(tokenized_xml, title='Book'):
    """Do a simple and not at all foolproof conversion to XHTML."""
    tokenized_xml.tag = 'html'
    tokenized_xml.attrib['xmlns'] = 'http://www.w3.org/1999/xhtml'
    for elem in tokenized_xml.iter():
        spans = {'u', 's', 'm', 'w'}
        if elem.tag == 's':
            elem.tag = 'p'
        elif elem.tag in spans:
            elem.tag = 'span'
    # Wrap everything in a <body> element
    body = etree.Element('body')
    for elem in tokenized_xml:
        body.append(elem)
    tokenized_xml.append(body)
    head = etree.Element('head')
    tokenized_xml.insert(0, head)
    title_element = etree.Element('head')
    title_element.text = title
    head.append(title_element)
    link_element = etree.Element('link')
    link_element.attrib['rel'] = 'stylesheet'
    link_element.attrib['href'] = 'stylesheet.css'
    link_element.attrib['type'] = 'text/css'
    head.append(link_element)


XML_TEMPLATE = """<document>
{{#sentences}}
<s{{#lang}} xml:lang="{{lang}}"{{/lang}}>{{text}}</s>
{{/sentences}}
</document>
"""


def create_input_xml(inputfile, text_language=None, save_temps=None):
    if save_temps:
        filename = save_temps + '.input.xml'
        outfile = io.open(filename, 'wb')
    else:
        outfile = NamedTemporaryFile(prefix='readalongs_xml_',
                                     suffix='.xml')
        filename = outfile.name
    with io.open(inputfile) as fin:
        text = []
        para = []
        for line in fin:
            line = line.strip()
            if line == "":
                text.append(' '.join(para))
                del para[:]
            else:
                para.append(line)
        if para:
            text.append(' '.join(para))
        sentences = []
        for p in text:
            data = {"text": p}
            if text_language is not None:
                data["lang"] = text_language
            sentences.append(data)
        xml = pystache.render(XML_TEMPLATE,
                              {'sentences': sentences})
        outfile.write(xml.encode('utf-8'))
        outfile.flush()
    return outfile, filename
