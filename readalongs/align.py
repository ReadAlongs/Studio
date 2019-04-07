"""
Alignment for audiobooks
"""

import pocketsphinx
import logging
import wave
import os
from lxml import etree
from tempfile import NamedTemporaryFile

from .g2p.tokenize_xml import tokenize_xml
from .g2p.add_ids_to_xml import add_ids
from .g2p.convert_xml import convert_xml
from .g2p.make_fsg import make_fsg
from .g2p.make_dict import make_dict
from . import mapping_dir

def do_g2p(xml):
    """Tokenize and convert words to phone sequences in an XML file."""
    xml = tokenize_xml(xml, mapping_dir)
    xml = add_ids(xml)
    xml = convert_xml(mapping_dir, xml)
    return xml

def align_audio(xml_path, wav_path, unit='w'):
    """End-to-end alignment of a single audio file."""
    # First do G2P
    xml = etree.parse(xml_path).getroot()
    xml = do_g2p(xml)
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
    results = { "words": [] }
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
