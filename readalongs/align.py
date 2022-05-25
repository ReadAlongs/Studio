"""Main readalongs module for aligning text and audio."""

import copy
import io
import os
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Union

import chevron
import regex as re
import soundswallower
from lxml import etree
from pydub import AudioSegment
from pydub.exceptions import CouldntEncodeError
from pympi.Praat import TextGrid
from webvtt import Caption, WebVTT

from readalongs.audio_utils import (
    extract_section,
    mute_section,
    read_audio_from_file,
    remove_section,
    write_audio_to_file,
)
from readalongs.dna_utils import (
    calculate_adjustment,
    correct_adjustments,
    dna_union,
    segment_intersection,
    sort_and_join_dna_segments,
)
from readalongs.log import LOGGER
from readalongs.portable_tempfile import PortableNamedTemporaryFile
from readalongs.text.add_elements_to_xml import add_images, add_supplementary_xml
from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.convert_xml import convert_xml
from readalongs.text.make_dict import make_dict
from readalongs.text.make_fsg import make_fsg
from readalongs.text.make_package import create_web_component_html
from readalongs.text.make_smil import make_smil
from readalongs.text.tokenize_xml import tokenize_xml
from readalongs.text.util import parse_time, save_minimal_index_html, save_txt, save_xml


@dataclass
class WordSequence:
    """Sequence of "unit" XML elements

    By default, the unit elements are the <w> elements.

    Attributes:
        start (int): Optional; start time in ms for the sequence - 0 if None
        end (int): Optional; end time in ms for the sequence - end of audio if None
        words (List): list of elements in the sequence
    """

    start: Union[int, None]
    end: Union[int, None]
    words: List


def get_sequences(xml, xml_filename, unit="w", anchor="anchor") -> List[WordSequence]:
    """Return the list of anchor-separated word sequences in xml

    Args:
        xml (etree): xml structure in which to search for words and anchors
        xml_filename (str): filename, used for error messages only
        unit (str): element tag of the word units
        anchor (str): element tag of the anchors

    Returns:
        List[WordSequence]: all sequences found in xml
    """

    sequences: List[WordSequence] = []
    start = None
    words = []
    all_good = True
    for e in xml.xpath(f".//{unit} | .//{anchor}"):
        if e.tag == unit:
            words.append(e)
        else:
            assert e.tag == anchor
            try:
                end = parse_time(e.attrib["time"])
            except KeyError:
                LOGGER.error(
                    f'Invalid {anchor} element in {xml_filename}: missing "time" attribute'
                )
                all_good = False
                continue
            except ValueError as err:
                LOGGER.error(
                    f'Invalid {anchor} element in {xml_filename}: invalid "time" '
                    f'attribute "{e.attrib["time"]}": {err}'
                )
                all_good = False
                continue
            if words:
                sequences.append(WordSequence(start, end, words))
            words = []
            start = end
    if words:
        sequences.append(WordSequence(start, None, words))

    if not all_good:
        raise RuntimeError(
            f"Could not parse all anchors in {xml_filename}, please make sure each anchor "
            'element is properly formatted, e.g., <anchor time="34.5s"/>.  Aborting.'
        )

    return sequences


def split_silences(words: List[dict], final_end, excluded_segments: List[dict]) -> None:
    """split the silences between words, making sure we don't step over any
        excluded segment boundaries

    Args:
        words(List[dict]): word list, with each word having ["start"] and ["end"] times
            in seconds. Modified in place.
        final_end(float): end of last segment from SoundSwallower, possibly a silence,
            in seconds
        excluded_segments: list of segments to exclude, having ["begin"] and ["end"]
            times in milliseconds
    """
    last_end = 0.0
    last_word: dict = {}
    words.append({"id": "dummy", "start": final_end, "end": final_end})
    for word in words:
        start = word["start"]
        if start > last_end:
            gap = start - last_end
            midpoint = round(last_end + gap / 2, 3)
            excluded_within_gap = segment_intersection(
                [{"begin": last_end * 1000, "end": start * 1000}], excluded_segments
            )
            if not excluded_within_gap:
                # Base case, there were no excluded segments between last_word and word
                if last_word:
                    last_word["end"] = midpoint
                word["start"] = midpoint
            else:
                if last_word:
                    last_word["end"] = min(
                        midpoint, excluded_within_gap[0]["begin"] / 1000
                    )
                word["start"] = max(midpoint, excluded_within_gap[-1]["end"] / 1000)
        last_word = word
        last_end = word["end"]
    _ = words.pop()


def align_audio(  # noqa: C901
    xml_path,
    audio_path,
    unit="w",
    bare=False,
    config=None,
    save_temps=None,
    verbose_g2p_warnings=False,
    debug_aligner=False,
):
    """Align an XML input file to an audio file.

    Args:
        xml_path (str): Path to XML input file in TEI-like format
        audio_path (str): Path to audio input. Must be in a format supported by ffmpeg
        unit (str): Optional; Element to create alignments for, by default 'w'
        bare (boolean): Optional;
            If False, split silence into adjoining tokens (default)
            If True, keep the bare tokens without adjoining silences.
        config (object): Optional; ReadAlong-Studio configuration to use
        save_temps (str): Optional; Save temporary files, by default None
        verbose_g2p_warnings (boolean): Optional; display all g2p errors and warnings
            iff True

    Returns:
        Dict[str, List]: TODO

    Raises:
        TODO
    """
    results: Dict[str, List] = {"words": [], "audio": None}
    if config is None:
        config = {}

    # First do G2P
    try:
        xml = etree.parse(xml_path).getroot()
    except etree.XMLSyntaxError as e:
        raise RuntimeError(
            "Error parsing XML input file %s: %s." % (xml_path, e)
        ) from e
    if "images" in config:
        xml = add_images(xml, config)
    if "xml" in config:
        xml = add_supplementary_xml(xml, config)
    xml = tokenize_xml(xml)
    if save_temps:
        save_xml(save_temps + ".tokenized.xml", xml)
    results["tokenized"] = xml = add_ids(xml)
    if save_temps:
        save_xml(save_temps + ".ids.xml", xml)
    xml, valid = convert_xml(xml, verbose_warnings=verbose_g2p_warnings)
    if save_temps:
        save_xml(save_temps + ".g2p.xml", xml)
    if not valid:
        raise RuntimeError(
            "Some words could not be g2p'd correctly. Aborting. "
            "Run with --debug-g2p for more detailed g2p error logs."
        )

    # Prepare the SoundSwallower (formerly PocketSphinx) configuration
    cfg = soundswallower.Decoder.default_config()
    cfg.set_string(
        "-hmm",
        config.get(
            "acoustic_model", os.path.join(soundswallower.get_model_path(), "en-us")
        ),
    )
    cfg.set_float("-beam", 1e-100)
    cfg.set_float("-pbeam", 1e-100)
    cfg.set_float("-wbeam", 1e-80)

    if not debug_aligner:
        # With --debug-aligner, we display the SoundSwallower logs on screen, but
        # otherwise we redirect them away from the terminal.
        if save_temps and (sys.platform not in ("win32", "cygwin")):
            # With --save-temps, we save the SoundSwallower logs to a file.
            # This is buggy on Windows, so we don't do it on Windows variants
            ss_log = save_temps + ".soundswallower.log"
        else:
            # Otherwise, we send the SoundSwallower logs to the bit bucket.
            ss_log = os.devnull
        cfg.set_string("-logfn", ss_log)
        cfg.set_string("-loglevel", "DEBUG")

    # Read the audio file
    audio = read_audio_from_file(audio_path)
    audio = audio.set_channels(1).set_sample_width(2)
    audio_length_in_ms = len(audio.raw_data)
    #  Downsampling is (probably) not necessary
    cfg.set_float("-samprate", audio.frame_rate)

    # Process audio, silencing or removing any DNA segments
    dna_segments = []
    removed_segments = []
    if "do-not-align" in config:
        # Sort un-alignable segments and join overlapping ones
        dna_segments = sort_and_join_dna_segments(config["do-not-align"]["segments"])
        method = config["do-not-align"].get("method", "remove")
        # Determine do-not-align method
        if method == "mute":
            dna_method = mute_section
        elif method == "remove":
            dna_method = remove_section
        else:
            LOGGER.error("Unknown do-not-align method declared")
        # Process audio and save temporary files
        if method in ("mute", "remove"):
            processed_audio = audio
            # Process the DNA segments in reverse order so we don't have to correct
            # for previously processed ones when using the "remove" method.
            for seg in reversed(dna_segments):
                processed_audio = dna_method(
                    processed_audio, int(seg["begin"]), int(seg["end"])
                )
            if save_temps:
                _, ext = os.path.splitext(audio_path)
                try:
                    processed_audio.export(
                        save_temps + "_processed" + ext, format=ext[1:]
                    )
                except CouldntEncodeError:
                    try:
                        os.remove(save_temps + "_processed" + ext)
                    except BaseException:
                        pass
                    LOGGER.warning(
                        f"Couldn't find encoder for '{ext[1:]}', defaulting to 'wav'"
                    )
                    processed_audio.export(save_temps + "_processed" + ".wav")
            removed_segments = dna_segments
        audio_data = processed_audio
    else:
        audio_data = audio

    # Set the minimum FFT size (no longer necessary since
    # SoundSwallower 0.2, but we keep this here for compatibility with
    # old versions in case we need to debug things)
    frame_points = int(cfg.get_float("-samprate") * cfg.get_float("-wlen"))
    fft_size = 1
    while fft_size < frame_points:
        fft_size = fft_size << 1
    cfg.set_int("-nfft", fft_size)

    # Note: the frames are typically 0.01s long (i.e., the frame rate is typically 100),
    # while the audio segments manipulated using pydub are sliced and accessed in
    # millisecond intervals. For audio segments, the ms slice assumption is hard-coded
    # all over, while frames_to_time() is used to convert segment boundaries returned by
    # soundswallower, which are indexes in frames, into durations in seconds.
    frame_size = 1.0 / cfg.get_int("-frate")

    def frames_to_time(frames):
        return frames * frame_size

    # Extract the list of sequences of words in the XML
    word_sequences = get_sequences(xml, xml_path, unit=unit)
    end = 0
    for i, word_sequence in enumerate(word_sequences):

        i_suffix = "" if i == 0 else "." + str(i + 1)

        # Generate dictionary and FSG for the current sequence of words
        dict_data = make_dict(word_sequence.words, xml_path, unit=unit)
        if save_temps:
            dict_file = io.open(save_temps + ".dict" + i_suffix, "wb")
        else:
            dict_file = PortableNamedTemporaryFile(
                prefix="readalongs_dict_", delete=False
            )
        dict_file.write(dict_data.encode("utf-8"))
        dict_file.close()

        fsg_data = make_fsg(word_sequence.words, xml_path)
        if save_temps:
            fsg_file = io.open(save_temps + ".fsg" + i_suffix, "wb")
        else:
            fsg_file = PortableNamedTemporaryFile(
                prefix="readalongs_fsg_", delete=False
            )
        fsg_file.write(fsg_data.encode("utf-8"))
        fsg_file.close()

        # Extract the part of the audio corresponding to this word sequence
        audio_segment = extract_section(
            audio_data, word_sequence.start, word_sequence.end
        )
        if save_temps and audio_segment is not audio_data:
            write_audio_to_file(audio_segment, save_temps + ".wav" + i_suffix)

        # Configure soundswallower for this sequence's dict and fsg
        cfg.set_string("-dict", dict_file.name)
        cfg.set_string("-fsg", fsg_file.name)
        cfg.set_int("-remove_noise", 0)
        cfg.set_int("-remove_silence", 0)
        ps = soundswallower.Decoder(cfg)
        # Align this word sequence
        ps.start_utt()
        ps.process_raw(audio_segment.raw_data, no_search=False, full_utt=True)
        ps.end_utt()

        if not ps.seg():
            raise RuntimeError(
                "Alignment produced no segments, "
                "please examine dictionary and input audio and text."
            )

        # List of removed segments for the sequence we are currently processing
        curr_removed_segments = dna_union(
            word_sequence.start, word_sequence.end, audio_length_in_ms, removed_segments
        )

        prev_segment_count = len(results["words"])
        for seg in ps.seg():
            if seg.word in ("<sil>", "[NOISE]"):
                continue
            start = frames_to_time(seg.start_frame)
            end = frames_to_time(seg.end_frame + 1)
            # change to ms
            start_ms = start * 1000
            end_ms = end * 1000
            if curr_removed_segments:
                start_ms += calculate_adjustment(start_ms, curr_removed_segments)
                end_ms += calculate_adjustment(end_ms, curr_removed_segments)
                start_ms, end_ms = correct_adjustments(
                    start_ms, end_ms, curr_removed_segments
                )
                # change back to seconds to write to smil
                start = start_ms / 1000
                end = end_ms / 1000
            results["words"].append({"id": seg.word, "start": start, "end": end})
            if debug_aligner:
                LOGGER.info("Segment: %s (%.3f : %.3f)", seg.word, start, end)
        aligned_segment_count = len(results["words"]) - prev_segment_count
        if aligned_segment_count != len(word_sequence.words):
            LOGGER.warning(
                f"Word sequence {i+1} had {len(word_sequence.words)} tokens "
                f"but produced {aligned_segment_count} segments. "
                "Check that the anchors are well positioned or "
                "that the audio corresponds to the text."
            )
    final_end = end

    aligned_segment_count = len(results["words"])
    token_count = len(results["tokenized"].xpath("//" + unit))
    LOGGER.info(f"Number of words found: {token_count}")
    LOGGER.info(f"Number of aligned segments: {aligned_segment_count}")

    if aligned_segment_count == 0:
        raise RuntimeError(
            "Alignment produced only noise or silence segments, "
            "please verify that the text is an actual transcript of the audio."
        )
    if aligned_segment_count != token_count:
        LOGGER.warning(
            "Alignment produced a different number of segments and tokens than "
            "were in the input. Sequences between some anchors probably did not "
            "align successfully. Look for more anchors-related warnings above in the log."
        )

    if not bare:
        # Take all the boundaries (anchors) around segments and add them as DNA
        # segments for the purpose of splitting silences
        dna_for_silence_splitting = copy.deepcopy(dna_segments)
        last_end = None
        for seq in word_sequences:
            if last_end or seq.start:
                dna_for_silence_splitting.append(
                    {"begin": (last_end or seq.start), "end": (seq.start or last_end)}
                )
            last_end = seq.end
        if last_end:
            dna_for_silence_splitting.append({"begin": last_end, "end": last_end})
        dna_for_silence_splitting = sort_and_join_dna_segments(
            dna_for_silence_splitting
        )

        split_silences(results["words"], final_end, dna_for_silence_splitting)
    words_dict = {
        x["id"]: {"start": x["start"], "end": x["end"]} for x in results["words"]
    }
    silence_offsets = defaultdict(int)
    silence = 0
    if results["tokenized"].xpath("//silence"):
        endpoint = 0
        all_good = True
        for el in results["tokenized"].xpath("//*"):
            if el.tag == "silence" and "dur" in el.attrib:
                try:
                    silence_ms = parse_time(el.attrib["dur"])
                except ValueError as err:
                    LOGGER.error(
                        f'Invalid silence element in {xml_path}: invalid "time" '
                        f'attribute "{el.attrib["dur"]}": {err}'
                    )
                    all_good = False
                    continue
                silence_segment = AudioSegment.silent(
                    duration=silence_ms
                )  # create silence segment
                silence += silence_ms  # add silence length to total silence
                audio = (
                    audio[:endpoint] + silence_segment + audio[endpoint:]
                )  # insert silence at previous endpoint
                endpoint += silence_ms  # add silence to previous endpoint
            if el.tag == "w":
                silence_offsets[el.attrib["id"]] += (
                    silence / 1000
                )  # add silence in seconds to silence offset for word id
                endpoint = (
                    words_dict[el.attrib["id"]]["end"] * 1000
                ) + silence  # bump endpoint and include silence
        if not all_good:
            raise RuntimeError(
                f"Could not parse all duration attributes in silence elements in {xml_path}, please make sure each silence "
                'element is properly formatted, e.g., <silence dur="1.5s"/>.  Aborting.'
            )
    if silence:
        for word in results["words"]:
            word["start"] += silence_offsets[word["id"]]
            word["end"] += silence_offsets[word["id"]]
        results["audio"] = audio
    return results


def save_readalong(  # noqa C901
    # noqa C901 - ignore the complexity of this function
    # this * forces all arguments to be passed by name, because I don't want any
    # code to depend on their order in the future
    *,
    align_results: Dict[str, List],
    output_dir: str,
    output_basename: str,
    config=None,
    audiofile: str,
    audiosegment: AudioSegment = None,
    output_formats=(),
):
    """Save the results from align_audio() into the output files required for a
        readalong

    Args:
        align_results(Dict[str,List]): return value from align_audio()
        output_dir (str): directory where to save the readalong,
            output_dir should already exist, files it contains may be overwritten
        output_basename (str): basename of the files to save in output_dir
        config ([type TODO], optional): alignment configuration loaded from the json
        audiofile (str): path to the audio file passed to align_audio()
        output_formats (List[str], optional): list of desired output formats
        audiosegment (AudioSegment): a pydub.AudioSegment object of processed audio.
                              if None, then original audio will be saved at `audiofile`

    Returns:
        None

    Raises:
        [TODO]
    """
    if config is None:
        config = {}
    # Round all times to three digits, anything more is excess precision
    # poluting the output files, and usually due to float rounding errors anyway.
    for w in align_results["words"]:
        w["start"] = round(w["start"], 3)
        w["end"] = round(w["end"], 3)

    output_base = os.path.join(output_dir, output_basename)

    # Create textgrid object if outputting to TextGrid or eaf
    if "textgrid" in output_formats or "eaf" in output_formats:
        audio = read_audio_from_file(audiofile)
        duration = audio.frame_count() / audio.frame_rate
        words, sentences = return_words_and_sentences(align_results)
        textgrid = write_to_text_grid(words, sentences, duration)

        if "textgrid" in output_formats:
            textgrid.to_file(output_base + ".TextGrid")

        if "eaf" in output_formats:
            textgrid.to_eaf().to_file(output_base + ".eaf")

    # Create webvtt object if outputting to vtt or srt
    if "srt" in output_formats or "vtt" in output_formats:
        words, sentences = return_words_and_sentences(align_results)
        cc_sentences = write_to_subtitles(sentences)
        cc_words = write_to_subtitles(words)

        if "srt" in output_formats:
            cc_sentences.save_as_srt(output_base + "_sentences.srt")
            cc_words.save_as_srt(output_base + "_words.srt")

        if "vtt" in output_formats:
            cc_words.save(output_base + "_words.vtt")
            cc_sentences.save(output_base + "_sentences.vtt")

    tokenized_xml_path = output_base + ".xml"
    save_xml(tokenized_xml_path, align_results["tokenized"])

    if "xhtml" in output_formats:
        convert_to_xhtml(align_results["tokenized"])
        tokenized_xhtml_path = output_base + ".xhtml"
        save_xml(tokenized_xhtml_path, align_results["tokenized"])

    _, audio_ext = os.path.splitext(audiofile)
    audio_path = output_base + audio_ext
    audio_format = audio_ext[1:]
    if audiosegment:
        if audio_format in ["m4a", "aac"]:
            audio_format = "ipod"
        try:
            audiosegment.export(audio_path, format=audio_format)
        except CouldntEncodeError:
            LOGGER.warning(
                f"The audio file at {audio_path} could \
                not be exported in the {audio_format} format. \
                Please ensure your installation of ffmpeg has \
                the necessary codecs."
            )
            audio_path = output_base + ".wav"
            audiosegment.export(audio_path, format="wav")
    else:
        shutil.copy(audiofile, audio_path)

    smil_path = output_base + ".smil"
    smil = make_smil(
        os.path.basename(tokenized_xml_path),
        os.path.basename(audio_path),
        align_results,
    )
    save_txt(smil_path, smil)

    if "html" in output_formats:
        html_out_path = output_base + ".html"
        html_out = create_web_component_html(tokenized_xml_path, smil_path, audio_path)
        with open(html_out_path, "w") as f:
            f.write(html_out)

    save_minimal_index_html(
        os.path.join(output_dir, "index.html"),
        os.path.basename(tokenized_xml_path),
        os.path.basename(smil_path),
        os.path.basename(audio_path),
    )

    # Copy the image files to the output's asset directory, if any are found
    if "images" in config:
        assets_dir = os.path.join(output_dir, "assets")
        try:
            os.mkdir(assets_dir)
        except FileExistsError:
            if not os.path.isdir(assets_dir):
                raise
        for _, image in config["images"].items():
            if image[0:4] == "http":
                LOGGER.warning(
                    f"Please make sure {image} is accessible to clients using your read-along."
                )
            else:
                try:
                    shutil.copy(image, assets_dir)
                except Exception as e:
                    LOGGER.warning(
                        f"Please copy {image} to {assets_dir} before deploying your read-along. ({e})"
                    )
                if os.path.basename(image) != image:
                    LOGGER.warning(
                        f"Read-along images were tested with absolute urls (starting with http(s):// "
                        f"and filenames without a path. {image} might not work as specified."
                    )


def return_word_from_id(xml: etree, el_id: str) -> str:
    """Given an XML document, return the innertext at id

    Args:
        xml (etree): XML document
        el_id (str): ID

    Returns:
        str: Innertext of element with el_id in xml
    """
    return xml.xpath('//*[@id="%s"]/text()' % el_id)[0]


def return_words_and_sentences(results):
    """Parse xml into word and sentence 'tier' data

    Args:
        results([TODO type]): [TODO description]

    Returns:
        [TODO type]: [TODO description]
    """
    result_id_pattern = re.compile(
        r"""
        t(?P<table>\d*)            # Table
        b(?P<body>\d*)             # Body
        d(?P<div>\d*)              # Div ( Break )
        p(?P<par>\d*)              # Paragraph
        s(?P<sent>\d+)             # Sentence
        w(?P<word>\d+)             # Word
        """,
        re.VERBOSE,
    )

    all_els = results["words"]
    xml = results["tokenized"]
    sentences = []
    words = []
    all_words = []
    current_sent = 0
    for el in all_els:
        parsed = re.search(result_id_pattern, el["id"])
        sent_i = parsed.group("sent")
        if int(sent_i) is not current_sent:
            sentences.append(words)
            words = []
            current_sent += 1
        word = {
            "text": return_word_from_id(xml, el["id"]),
            "start": el["start"],
            "end": el["end"],
        }
        words.append(word)
        all_words.append(word)
    sentences.append(words)
    return all_words, sentences


def write_to_text_grid(words: List[dict], sentences: List[dict], duration: float):
    """Write results to Praat TextGrid. Because we are using pympi, we can also export to Elan EAF.

    Args:
        words (List[dict]): List of word times containing start, end, and value keys
        sentences (List[dict]): List of sentence times containing start, end, and value keys
        duration (float): duration of entire audio

    Returns:
        TextGrid: Praat TextGrid with word and sentence alignments
    """
    text_grid = TextGrid(xmax=duration)
    sentence_tier = text_grid.add_tier(name="Sentence")
    word_tier = text_grid.add_tier(name="Word")
    for s in sentences:
        sentence_tier.add_interval(
            begin=s[0]["start"],
            end=s[-1]["end"],
            value=" ".join([w["text"] for w in s]),
        )

    for w in words:
        word_tier.add_interval(begin=w["start"], end=w["end"], value=w["text"])

    return text_grid


def float_to_timedelta(n: float) -> str:
    """Float to timedelta, for subtitle formats

    Args:
        n (float): any float

    Returns:
        str: timedelta string
    """
    td = timedelta(seconds=n)
    if not td.microseconds:
        return str(td) + ".000"
    return str(td)


def write_to_subtitles(data: Union[List[dict], List[List[dict]]]):
    """Returns WebVTT object from data.

    Args:
        data (Union[List[dict], List[List[dict]]]):
            data must be either a 'word'-type tier with
            a list of dicts that have keys for 'start', 'end' and
           'text'. Or a 'sentence'-type tier with a list of lists of dicts.

    Returns:
        WebVTT: WebVTT subtitles
    """
    vtt = WebVTT()
    for caption in data:
        if isinstance(caption, list):
            formatted = Caption(
                float_to_timedelta(caption[0]["start"]),
                float_to_timedelta(caption[-1]["end"]),
                " ".join([w["text"] for w in caption]),
            )
        else:
            formatted = Caption(
                float_to_timedelta(caption["start"]),
                float_to_timedelta(caption["end"]),
                caption["text"],
            )
        vtt.captions.append(formatted)
    return vtt


def convert_to_xhtml(tokenized_xml, title="Book"):
    """Do a simple and not at all foolproof conversion to XHTML.

    Args:
        tokenized_xml (etree): xml etree with tokens, converted in place
        title (str, optional): title for xhtml, by default 'Book'
    """
    tokenized_xml.tag = "html"
    tokenized_xml.attrib["xmlns"] = "http://www.w3.org/1999/xhtml"
    for elem in tokenized_xml.iter():
        spans = {"u", "s", "m", "w"}
        if elem.tag == "s":
            elem.tag = "p"
        elif elem.tag in spans:
            elem.tag = "span"
    # Wrap everything in a <body> element
    body = etree.Element("body")
    for elem in tokenized_xml:
        body.append(elem)
    tokenized_xml.append(body)
    head = etree.Element("head")
    tokenized_xml.insert(0, head)
    title_element = etree.Element("head")
    title_element.text = title
    head.append(title_element)
    link_element = etree.Element("link")
    link_element.attrib["rel"] = "stylesheet"
    link_element.attrib["href"] = "stylesheet.css"
    link_element.attrib["type"] = "text/css"
    head.append(link_element)


TEI_TEMPLATE = """<?xml version='1.0' encoding='utf-8'?>
<TEI>
    <!-- To exclude any element from alignment, add the do-not-align="true" attribute to
         it, e.g., <p do-not-align="true">...</p>, or
         <s>Some text <foo do-not-align="true">do not align this</foo> more text</s> -->
    <text xml:lang="{{main_lang}}" fallback-langs="{{fallback_langs}}">
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


def create_input_tei(**kwargs):
    """Create input xml in TEI standard.
        Uses readlines to infer paragraph and sentence structure from plain text.
        TODO: Check if path, if it's just plain text, then render that instead of reading from the file
        Assumes a double blank line marks a page break, and a single blank line
        marks a paragraph break.
        Outputs to uft-8 XML using pymustache.

    Args:
        **kwargs: dict containing these arguments:
            input_file_name (str, optional): input text file name
            input_file_handle (file_handle, optional): opened file handle for input text
                Only provide one of input_file_name or input_file_handle!
            text_languages (List[str]): language(s) for the text, in the order
                they should be attempted for g2p.
            save_temps (str, optional): prefix for output file name,
                which will be kept; or None to create a temporary file
            output_file (str, optional): if specified, the output file
                will have exactly this name

    Returns:
        file: outfile (file handle)
        str: output file name
    """
    try:
        if kwargs.get("input_file_name", False):
            filename = kwargs["input_file_name"]
            with io.open(kwargs["input_file_name"], encoding="utf8") as f:
                text = f.readlines()
        elif kwargs.get("input_file_handle", False):
            filename = kwargs["input_file_handle"].name
            text = kwargs["input_file_handle"].readlines()
        else:
            assert False, "need one of input_file_name or input_file_handle"
    except UnicodeDecodeError as e:
        raise RuntimeError(
            f"Cannot read {filename} as utf-8 plain text: {e}. "
            "Please make sure to provide a correctly encoded utf-8 plain text input file."
        ) from e

    text_langs = kwargs.get("text_languages", None)
    assert text_langs and isinstance(text_langs, (list, tuple)), "need text_languages"

    kwargs["main_lang"] = text_langs[0]
    kwargs["fallback_langs"] = ",".join(text_langs[1:])

    save_temps = kwargs.get("save_temps", False)
    if kwargs.get("output_file", False):
        filename = kwargs.get("output_file")
        outfile = io.open(filename, "wb")
    elif save_temps:
        filename = save_temps + ".input.xml"
        outfile = io.open(filename, "wb")
    else:
        outfile = PortableNamedTemporaryFile(
            prefix="readalongs_xml_", suffix=".xml", delete=True
        )
        filename = outfile.name
    pages = []
    paragraphs = []
    sentences = []
    for line in text:
        if line == "\n":
            if not sentences:
                # consider this a page break (unless at the beginning)
                pages.append({"paragraphs": paragraphs})
                paragraphs = []
            else:
                # add sentences and begin new paragraph
                paragraphs.append({"sentences": sentences})
                sentences = []
        else:
            # Add text to sentence
            sentences.append(line.strip())
    # Add the last paragraph/sentence
    if sentences:
        paragraphs.append({"sentences": sentences})
    if paragraphs:
        pages.append({"paragraphs": paragraphs})
    xml = chevron.render(TEI_TEMPLATE, {**kwargs, **{"pages": pages}})
    outfile.write(xml.encode("utf-8"))
    outfile.flush()
    outfile.close()
    return outfile, filename
