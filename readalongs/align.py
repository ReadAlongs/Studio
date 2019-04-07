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
from readalongs import mapping_dir

def align_audio(xml_path, wav_path, unit='w'):
    """End-to-end alignment of a single audio file."""
    results = { "words": [] }
    # First do G2P
    xml = etree.parse(xml_path).getroot()
    xml = tokenize_xml(xml, mapping_dir)
    results['tokenized'] = xml = add_ids(xml)
    xml = convert_xml(mapping_dir, xml)
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
    ps = pocketsphinx.Decoder(cfg)
    lmath = ps.get_logmath()
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

def make_argparse():
    """Hey! This function makes the argparse!"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputfile', type=str, help='Input file (XML or text)')
    parser.add_argument('wavfile', type=str, help='Input audio file')
    parser.add_argument('outputfile', type=str, help='Base name for output files')
    parser.add_argument('-f', '--force-overwrite',
                        action='store_true',
                        help='Force overwriting existing output files')
    parser.add_argument('--text-input', action='store_true',
                        help='Input is plain text (assume one sentence per line)')
    parser.add_argument('--text-language', type=str,
                        help='Set language for plain text input')
    return parser

XML_TEMPLATE = """<document>
{{#sentences}}
<s xml:lang="{{lang}}">{{text}}</s>
{{/sentences}}
</document>
"""

def main(argv=None):
    """Hey! This function is named main!"""
    parser = make_argparse()
    args = parser.parse_args(argv)
    if args.text_input:
        if args.text_language is None:
            parser.error("--text-input requires --text-language")
        tempfile = NamedTemporaryFile(prefix='readalongs_xml_')
        with io.open(args.inputfile) as fin:
            data = { "sentences":
                     [{ "text":text, "lang":args.text_language}
                      for text in fin if text.strip() != ""] }
            xml = pystache.render(XML_TEMPLATE, data)
            tempfile.write(xml.encode('utf-8'))
            tempfile.flush()
        args.inputfile = tempfile.name

    tokenized_xml_path = args.outputfile + '.xml'
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
    with io.open(tokenized_xml_path, 'w', encoding='utf-8') as fout:
        fout.write(etree.tounicode(results['tokenized']))
    smil = make_smil(os.path.basename(tokenized_xml_path),
                     os.path.basename(wav_path), results)
    shutil.copy(args.wavfile, wav_path)
    with io.open(smil_path, 'w', encoding='utf-8') as fout:
        fout.write(smil)

if __name__ == '__main__':
    main()
