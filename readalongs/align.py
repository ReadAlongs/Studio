"""
Alignment for audiobooks
"""

import pocketsphinx
import argparse
import pystache
import shutil
import pydub
import wave
import os
import io

from lxml import etree
from tempfile import NamedTemporaryFile

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
    xml = etree.parse(xml_path).getroot()
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
    else:  # Try pydub, it might fail
        audio = pydub.AudioSegment.from_file(wav_path)
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

    try:
        final_end = end
    except UnboundLocalError:
        err = RuntimeError("Alignment Failed, please examine "
                           "dictionary and input audio and text.")
        LOGGER.exception(err)
        raise err

    # FIXME: should have the same number of outputs as inputs
    if len(results['words']) == 0:
        raise RuntimeError("Alignment Failed, please examine "
                           "dictionary and input audio and text.")

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


def make_argparse():
    """Hey! This function makes the argparse!"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputfile', type=str, help='Input file (XML or text)')
    parser.add_argument('wavfile', type=str, help='Input audio file')
    parser.add_argument('outputfile', type=str,
                        help='Base name for output files')
    parser.add_argument('--debug', action='store_true',
                        help='Enable extra debugging logging')
    parser.add_argument('-s', '--save-temps', action='store_true',
                        help='Save intermediate stages of processing and '
                        'temporary files (dictionary, FSG, tokenization etc)')
    parser.add_argument('-f', '--force-overwrite',
                        action='store_true',
                        help='Force overwriting existing output files')
    parser.add_argument(
        '--text-input', action='store_true',
        help='Input is plain text (assume paragraphs '
        'separated by blank lines)')
    parser.add_argument('--text-language', type=str,
                        help='Set language for plain text input')
    parser.add_argument('--output-xhtml', action='store_true',
                        help='Output simple XHTML instead of XML')
    return parser


def main(argv=None):
    """Hey! This function is named main!"""
    parser = make_argparse()
    args = parser.parse_args(argv)
    if args.debug:
        LOGGER.setLevel('DEBUG')
    if args.text_input:
        tempfile, args.inputfile \
            = create_input_xml(args.inputfile,
                               text_language=args.text_language,
                               save_temps=(args.outputfile
                                           if args.save_temps else None))
    if args.output_xhtml:
        tokenized_xml_path = '%s.xhtml' % args.outputfile
    else:
        _, input_ext = os.path.splitext(args.inputfile)
        tokenized_xml_path = '%s%s' % (args.outputfile, input_ext)
    if os.path.exists(tokenized_xml_path) and not args.force_overwrite:
        parser.error("Output file %s exists already, did you mean to do that?"
                     % tokenized_xml_path)
    smil_path = args.outputfile + '.smil'
    if os.path.exists(smil_path) and not args.force_overwrite:
        parser.error("Output file %s exists already, did you mean to do that?"
                     % smil_path)
    _, wav_ext = os.path.splitext(args.wavfile)
    wav_path = args.outputfile + wav_ext
    if os.path.exists(wav_path) and not args.force_overwrite:
        parser.error("Output file %s exists already, did you mean to do that?"
                     % wav_path)

    results = align_audio(args.inputfile, args.wavfile,
                          save_temps=(args.outputfile
                                      if args.save_temps else None))
    if args.output_xhtml:
        convert_to_xhtml(results['tokenized'])
    save_xml(tokenized_xml_path, results['tokenized'])
    smil = make_smil(os.path.basename(tokenized_xml_path),
                     os.path.basename(wav_path), results)
    shutil.copy(args.wavfile, wav_path)
    save_txt(smil_path, smil)


if __name__ == '__main__':
    main()
