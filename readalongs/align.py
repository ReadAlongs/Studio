#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# align.py
#
#   This is the main module for aligning text and audio
#
#######################################################################

from readalongs.tempfile import PortableNamedTemporaryFile
from datetime import timedelta
from typing import List, Union
import os
import io

from webvtt import WebVTT, Caption
from pympi.Praat import TextGrid
from pydub.exceptions import CouldntEncodeError
from lxml import etree
import soundswallower
import regex as re
import pystache

from readalongs.audio_utils import mute_section, read_audio_from_file, remove_section
from readalongs.text.tokenize_xml import tokenize_xml
from readalongs.text.convert_xml import convert_xml
from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.lang_id import add_lang_ids
from readalongs.text.make_dict import make_dict
from readalongs.text.make_fsg import make_fsg
from readalongs.text.util import save_xml
from readalongs.log import LOGGER


def correct_adjustments(start: int, end: int, do_not_align_segments: List[object]) -> (int, int):
    """ Given the start and end of a segment (in ms) and a list of do-not-align segments,
        If one of the do-not-align segments occurs inside one of the start-end range,
        align the start or end with the do-not-align segment, whichever requires minimal change
    """
    for seg in do_not_align_segments:
        if start < seg['begin'] and end > seg['end']:
            if seg['begin'] - start > end - seg['end']:
                return start, seg['begin']
            else:
                return seg['end'], end
    return start, end


def calculate_adjustment(timestamp: int, do_not_align_segments: List[object]) -> int:
    """ Given a time (in ms) and a list of do-not-align segments,
        return the sum (ms) of the lengths of the do-not-align segments 
        that start before the timestamp
    """
    return sum(
        (seg['end'] - seg['begin'])
        for seg in do_not_align_segments
        if seg['begin'] <= timestamp
    )


def align_audio(xml_path: str, audio_path: str, unit: str = 'w', bare=False, config=None, save_temps: Union[str, None] = None):
    """ Align an XML input file to an audio file.

    Parameters
    ----------
    xml_path : str
        Path to XML input file in TEI-like format
    audio_path : str
        Path to audio input. Must be in a format supported by ffmpeg
    unit : str, optional
        Element to create alignments for, by default 'w'
    bare : boolean, optional
        If False, split silence into adjoining tokens (default)
        If True, keep the bare tokens without adjoining silences.
    config : object, optional
        Uses ReadAlong-Studio configuration
    save_temps : Union[str, None], optional
        save temporary files, by default None

    #TODO: document return
    Returns
    -------
    [type]
        [description]

    #TODO: document exceptions
    Raises
    ------
    RuntimeError
        [description]
    RuntimeError
        [description]
    RuntimeError
        [description]
    RuntimeError
        [description]
    """
    results = {"words": []}

    # First do G2P
    try:
        xml = etree.parse(xml_path).getroot()
    except etree.XMLSyntaxError as e:
        raise RuntimeError(
            "Error parsing XML input file %s: %s." % (xml_path, e))
    xml = add_lang_ids(xml, unit="s")
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
        dict_file = PortableNamedTemporaryFile(
            prefix='readalongs_dict_', delete=False)
    dict_file.write(dict_data.encode('utf-8'))
    dict_file.flush()
    fsg_data = make_fsg(xml, xml_path, unit=unit)
    if save_temps:
        fsg_file = io.open(save_temps + '.fsg', 'wb')
    else:
        fsg_file = PortableNamedTemporaryFile(
            prefix='readalongs_fsg_', delete=False)
    fsg_file.write(fsg_data.encode('utf-8'))
    fsg_file.flush()

    # Now do alignment
    cfg = soundswallower.Decoder.default_config()
    model_path = soundswallower.get_model_path()
    cfg.set_boolean('-remove_noise', False)
    cfg.set_boolean('-remove_silence', False)
    cfg.set_string('-hmm', os.path.join(model_path, 'en-us'))
    cfg.set_string('-dict', dict_file.name)
    cfg.set_string('-fsg', fsg_file.name)
    # cfg.set_string('-samprate', "no no")
    cfg.set_float('-beam', 1e-100)
    cfg.set_float('-wbeam', 1e-80)

    audio = read_audio_from_file(audio_path)
    audio = audio.set_channels(1).set_sample_width(2)
    #  Downsampling is (probably) not necessary
    cfg.set_float('-samprate', audio.frame_rate)

    # Process audio
    do_not_align_segments = None
    if config and "do-not-align" in config:
        # Reverse sort un-alignable segments
        do_not_align_segments = sorted(
            config['do-not-align']['segments'], key=lambda x: x['begin'], reverse=True)
        method = config['do-not-align'].get('method', 'remove')
        # Determine do-not-align method
        if method == 'mute':
            dna_method = mute_section
        elif method == 'remove':
            dna_method = remove_section
        else:
            LOGGER.error(f'Unknown do-not-align method declared')
            dna_method = None
        # Process audio and save temporary files
        if dna_method:
            processed_audio = audio
            for seg in do_not_align_segments:
                processed_audio = dna_method(
                    processed_audio, int(seg['begin']), int(seg['end']))
            if save_temps:
                _, ext = os.path.splitext(audio_path)
                try:
                    processed_audio.export(
                        save_temps + '_processed' + ext, format=ext[1:])
                except CouldntEncodeError:
                    os.remove(save_temps + '_processed' + ext)
                    LOGGER.warn(
                        f"Couldn't find encoder for '{ext[1:]}', defaulting to 'wav'")
                    processed_audio.export(save_temps + '_processed' + '.wav')
        raw_data = processed_audio.raw_data
    else:
        raw_data = audio.raw_data

    frame_points = int(cfg.get_float('-samprate')
                       * cfg.get_float('-wlen'))
    fft_size = 1
    while fft_size < frame_points:
        fft_size = fft_size << 1
    cfg.set_int('-nfft', fft_size)
    ps = soundswallower.Decoder(cfg)
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
        # change to ms
        start_ms = start * 1000
        end_ms = end * 1000
        if do_not_align_segments and method == 'remove':
            start_ms += (calculate_adjustment(start_ms,
                                           do_not_align_segments))
            end_ms += (calculate_adjustment(end_ms, do_not_align_segments))
            start_ms, end_ms = correct_adjustments(start_ms, end_ms, do_not_align_segments)
            # change back to seconds to write to smil
            start = start_ms / 1000
            end = end_ms / 1000
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
    if len(results['words']) != len(results['tokenized'].xpath('//' + unit)):
        raise RuntimeError("Alignment produced a different number of segments and tokens, "
                           "please examine dictionary and input audio and text.")

    final_end = end

    if not bare:
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
    if not save_temps:
        os.unlink(dict_file.name)
    fsg_file.close()
    if not save_temps:
        os.unlink(fsg_file.name)

    return results


def return_word_from_id(xml: etree, el_id: str) -> str:
    """ Given an XML document, return the innertext at id

    Parameters
    ----------
    xml : etree
        XML document
    el_id : str
        ID

    Returns
    -------
    str
        Innertext of element with el_id in xml
    """
    return xml.xpath('//*[@id="%s"]/text()' % el_id)[0]


def return_words_and_sentences(results):
    """ Parse xml into word and sentence 'tier' data

    #TODO: document params
    Parameters
    ----------
    results : [type]
        [description]

    #TODO: document return
    Returns
    -------
    [type]
        [description]
    """
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


def write_to_text_grid(words: List[dict], sentences: List[dict], duration: float):
    """ Write results to Praat TextGrid. Because we are using pympi, we can also export to Elan EAF.

    Parameters
    ----------
    words : List[dict]
        List of word times containing start, end, and value keys
    sentences : List[dict]
        List of sentence times containing start, end, and value keys
    duration : float
        duration of entire audio

    Returns
    -------
    TextGrid
        Praat TextGrid with word and sentence alignments
    """
    text_grid = TextGrid(xmax=duration)
    sentence_tier = text_grid.add_tier(name='Sentence')
    word_tier = text_grid.add_tier(name='Word')
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

    return text_grid


def float_to_timedelta(n: float) -> str:
    """Float to timedelta, for subtitle formats

    Parameters
    ----------
    n : float
        any float

    Returns
    -------
    str
        timedelta string
    """
    td = timedelta(seconds=n)
    if not td.microseconds:
        return str(td) + ".000"
    return str(td)


def write_to_subtitles(data: Union[List[dict], List[List[dict]]]):
    """ Returns WebVTT object from data.

    Parameters
    ----------
    data : Union[List[dict], List[List[dict]]]
        Data must be either a 'word'-type tier with
        a list of dicts that have keys for 'start', 'end' and
       'text'. Or a 'sentence'-type tier with a list of lists of dicts.

    Returns
    -------
    WebVTT
        WebVTT subtitles
    """
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
    """ Do a simple and not at all foolproof conversion to XHTML.

    Parameters
    ----------
    tokenized_xml : etree
        xml etree with tokens
    title : str, optional
        title for xhtml, by default 'Book'

    #TODO: AP: Should this be returning something? It's unused seemingly.
    """
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

TEI_TEMPLATE = """<?xml version='1.0' encoding='utf-8'?>
<TEI>
    <!-- To exclude any element from alignment, add the do-not-align="true" attribute to
         it, e.g., <p do-not-align="true">...</p>, or
         <s>Some text <foo do-not-align="true">do not align this</foo> more text</s> -->
    <text{{#text_language}} xml:lang="{{text_language}}"{{/text_language}}>
        <body>
        {{#pages}}
            <div type="page">
            {{#paragraphs}}
                <p>
                {{#sentences}}
                    <s>{{.}}</s>
                {{/sentences}}
                </p>
            {{/paragraphs}}
            </div>
        {{/pages}}
        </body>
    </text>
</TEI>
"""


def create_input_xml(inputfile: str, text_language: Union[str, None] = None, save_temps: Union[str, None] = None):
    """Create input XML

    Parameters
    ----------
    inputfile : str
        path to file
    text_language : Union[str, None], optional
        language of inputfile text, by default None
    save_temps : Union[str, None], optional
        save temporary files, by default None

    Returns
    -------
    file
        outfile
    str
        filename
    """
    if save_temps:
        filename = save_temps + '.input.xml'
        outfile = io.open(filename, 'wb')
    else:
        outfile = PortableNamedTemporaryFile(prefix='readalongs_xml_',
                                             suffix='.xml', delete=True)
        filename = outfile.name
    with io.open(inputfile, encoding="utf-8") as fin:
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
        outfile.close()
    return outfile, filename


def create_input_tei(text: str, **kwargs):
    """ Create input xml in TEI standard.
        Uses readlines to infer paragraph and sentence structure from plain text. 
        TODO: Check if path, if it's just plain text, then render that instead of reading from the file
        Assumes single page. 
        Outputs to uft-8 XML using pymustache. 

    Parameters
    ----------
    text : str
        raw input text
    **text_language in kwargs : str
        language for the text.
    **save_temps in kwargs : Union[str, None], optional
        prefix for output file name, which will be kept; or None to create a temporary file
    **output_file in kwargs : Union[str, None], optional
        if specified, the output file will have exactly this name
    
    Returns
    -------
    file
        outfile (file handle)
    str
        filename
    """
    with io.open(text, encoding="utf-8") as f:
        text = f.readlines()
    save_temps = kwargs.get('save_temps', False)
    if kwargs.get('output_file', False):
        filename = kwargs.get('output_file')
        outfile = io.open(filename, 'wb')
    elif save_temps:
        filename = save_temps + '.input.xml'
        outfile = io.open(filename, 'wb')
    else:
        outfile = PortableNamedTemporaryFile(prefix='readalongs_xml_',
                                             suffix='.xml', delete=True)
        filename = outfile.name
    pages = []
    paragraphs = []
    sentences = []
    for line in text:
        if line == '\n':
            if not sentences:
                # consider this a page break (unless at the beginning)
                pages.append({'paragraphs': paragraphs})
                paragraphs = []
            else:
                # add sentences and begin new paragraph
                paragraphs.append({'sentences': sentences})
                sentences = []
        else:
            # Add text to sentence
            sentences.append(line.strip())
    # Add the last paragraph/sentence
    if sentences:
        paragraphs.append({'sentences': sentences})
    if paragraphs:
        pages.append({'paragraphs': paragraphs})
    xml = pystache.render(TEI_TEMPLATE, {**kwargs, **{'pages': pages}})
    outfile.write(xml.encode('utf-8'))
    outfile.flush()
    outfile.close()
    return outfile, filename
