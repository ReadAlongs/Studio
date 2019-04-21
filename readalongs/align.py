"""
Alignment for audiobooks
"""

import pocketsphinx
import argparse
import logging
import pystache
import shutil
import wave
import os
import io

from lxml import etree
from tempfile import NamedTemporaryFile

from readalongs.g2p.tokenize_xml import tokenize_xml
from readalongs.g2p.add_ids_to_xml import add_ids
from readalongs.g2p.convert_xml import convert_xml
from readalongs.g2p.make_fsg import make_fsg
from readalongs.g2p.make_dict import make_dict
from readalongs.g2p.make_smil import make_smil
from readalongs.g2p.util import save_xml, save_txt

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


def align_audio(xml_path, wav_path, unit='w'):
    results = {"words": []}
    # First do G2P
    xml = etree.parse(xml_path).getroot()
    xml = tokenize_xml(xml)
    results['tokenized'] = xml = add_ids(xml)
    xml = convert_xml(xml)
    # Now generate dictionary and FSG
    dict_data = make_dict(xml, xml_path, unit=unit)
    dict_file = NamedTemporaryFile(prefix='readalongs_dict_')
    dict_file.write(dict_data.encode('utf-8'))
    dict_file.flush()
    fsg_data = make_fsg(xml, xml_path, unit=unit)
    fsg_file = NamedTemporaryFile(prefix='readalongs_fsg_')
    fsg_file.write(fsg_data.encode('utf-8'))
    fsg_file.flush()
    # Now do alignment (FIXME: need to straighten this out with the
    # PocketSphinx python modules)
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
    ps = pocketsphinx.Decoder(cfg)
    frame_size = 1.0 / cfg.get_int('-frate')
    logging.info("Model sample rate: %d, frame size: %f sec",
                 cfg.get_float('-samprate'), frame_size)

    def frames_to_time(frames):
        return frames * frame_size
    with wave.open(wav_path) as wav:
        # FIXME: Obvs need to convert/downsample as needed
        logging.info("Read %s: %d frames (%f seconds) audio"
                     % (wav_path, wav.getnframes(), wav.getnframes()
                        / wav.getframerate()))
        raw_data = wav.readframes(wav.getnframes())
        ps.start_utt()
        ps.process_raw(raw_data, no_search=False, full_utt=True)
        ps.end_utt()
    for seg in ps.seg():
        if seg.word in ('<sil>', '[NOISE]'):
            continue
        start = frames_to_time(seg.start_frame)
        end = frames_to_time(seg.end_frame + 1)
        results["words"].append({
            "id": seg.word,
            "start": start,
            "end": end
        })
        logging.info("Segment: %s (%.3f : %.3f)",
                     seg.word, start, end)
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


def make_argparse():
    """Hey! This function makes the argparse!"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputfile', type=str, help='Input file (XML or text)')
    parser.add_argument('wavfile', type=str, help='Input audio file')
    parser.add_argument('outputfile', type=str,
                        help='Base name for output files')
    parser.add_argument('--debug', action='store_true',
                        help='Enable extra debugging logging')
    parser.add_argument('-f', '--force-overwrite',
                        action='store_true',
                        help='Force overwriting existing output files')
    parser.add_argument(
        '--text-input', action='store_true',
        help='Input is plain text (assume paragraphs separated by blank lines)')
    parser.add_argument('--text-language', type=str,
                        help='Set language for plain text input')
    parser.add_argument('--output-xhtml', action='store_true',
                        help='Output simple XHTML instead of XML')
    return parser


XML_TEMPLATE = """<document>
{{#sentences}}
<s xml:lang="{{lang}}">{{text}}</s>
{{/sentences}}
</document>
"""


def create_input_xml(inputfile, text_language):
    tempfile = NamedTemporaryFile(prefix='readalongs_xml_',
                                  suffix='.xml')
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
        data = {"sentences":
                [{"text": para, "lang": text_language}
                 for para in text]}
        xml = pystache.render(XML_TEMPLATE, data)
        tempfile.write(xml.encode('utf-8'))
        tempfile.flush()
    return tempfile


def main(argv=None):
    """Hey! This function is named main!"""
    parser = make_argparse()
    args = parser.parse_args(argv)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    if args.text_input:
        if args.text_language is None:
            parser.error("--text-input requires --text-language")
        tempfile = create_input_xml(args.inputfile, args.text_language)
        args.inputfile = tempfile.name
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
    wav_path = args.outputfile + '.wav'
    if os.path.exists(wav_path) and not args.force_overwrite:
        parser.error("Output file %s exists already, did you mean to do that?"
                     % wav_path)

    results = align_audio(args.inputfile, args.wavfile)
    if args.output_xhtml:
        convert_to_xhtml(results['tokenized'])
    save_xml(tokenized_xml_path, results['tokenized'])
    smil = make_smil(os.path.basename(tokenized_xml_path),
                     os.path.basename(wav_path), results)
    shutil.copy(args.wavfile, wav_path)
    save_txt(smil_path, smil)


if __name__ == '__main__':
    main()
