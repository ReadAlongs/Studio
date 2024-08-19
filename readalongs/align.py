"""Main readalongs module for aligning text and audio."""

import copy
import io
import os
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

import chevron
import soundswallower
from lxml import etree
from pydub import AudioSegment
from pydub.exceptions import CouldntEncodeError
from pympi.Praat import TextGrid
from webvtt import Caption, WebVTT

from readalongs._version import READALONG_FILE_FORMAT_VERSION, VERSION
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
from readalongs.text.make_package import (
    DEFAULT_HEADER,
    DEFAULT_SUBHEADER,
    DEFAULT_TITLE,
    create_web_component_html,
)
from readalongs.text.tokenize_xml import tokenize_xml
from readalongs.text.util import (
    get_word_text,
    load_xml,
    parse_time,
    save_minimal_index_html,
    save_readme_txt,
    save_xml,
)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "static", "model")
DEFAULT_ACOUSTIC_MODEL = "cmusphinx-en-us-5.2"


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


def get_sequences(
    xml, xml_filename="memory", unit="w", anchor="anchor"
) -> List[WordSequence]:
    """Return the list of anchor-separated word sequences in xml

    Args:
        xml (etree.ElementTree): xml structure in which to search for words and anchors
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


def parse_and_make_xml(
    xml_path: str,
    config: dict,
    save_temps: Optional[str] = None,
    verbose_g2p_warnings: Optional[bool] = False,
    output_orthography: str = "eng-arpabet",
) -> etree.ElementTree:
    """Parse XML input and run tokenization and G2P.

    Args:
        xml_path (str): Path to input in ReadAlong XML format (see static/read-along-1.2.dtd)
        config (dict): Optional; ReadAlong-Studio configuration to use
        save_temps (str): Optional; Save temporary files, by default None
        verbose_g2p_warnings (boolean): Optional; display all g2p errors and warnings
            iff True

    Returns:
        lxml.etree.ElementTree: Parsed and prepared XML

    Raises:
        RuntimeError: If XML failed to parse"""
    # First do G2P
    try:
        xml = load_xml(xml_path)
    except etree.ParseError as e:
        raise RuntimeError(
            "Error parsing XML input file %s: %s." % (xml_path, e)
        ) from e
    if "images" in config:
        xml = add_images(xml, config)
    if "xml" in config:
        xml = add_supplementary_xml(xml, config)
    xml = tokenize_xml(xml)
    if save_temps is not None:
        save_xml(save_temps + ".tokenized.readalong", xml)
    xml = add_ids(xml)
    if save_temps is not None:
        save_xml(save_temps + ".ids.readalong", xml)
    xml, valid = convert_xml(
        xml,
        verbose_warnings=verbose_g2p_warnings,
        output_orthography=output_orthography,
    )
    if save_temps is not None:
        save_xml(save_temps + ".g2p.readalong", xml)
    if not valid:
        raise RuntimeError(
            "Some words could not be g2p'd correctly. Aborting. "
            "Run with --debug-g2p for more detailed g2p error logs."
        )
    return xml


def create_asr_config(
    config: dict,
    audio: AudioSegment,
    save_temps: Optional[str] = None,
    debug_aligner: Optional[bool] = False,
    alignment_mode: str = "auto",
) -> soundswallower.Config:
    """Create the base SoundSwallower (formerly PocketSphinx) configuration.

    Args:
        config (dict): ReadAlong-Studio configuration to use.
        audio (AudioSegment): Audio input from which to take parameters.
        save_temps (str): Optional; Prefix for saving temporary files, by default None.
        debug_aligner (boolean): Optional; Output debugging info from the aligner.
        alignment_mode (str): Optional, controls the decoder beam width

    Returns:
        soundswallower.Config: Basic configuration."""
    asr_config = soundswallower.Config()
    acoustic_model = config.get(
        "acoustic_model", os.path.join(MODEL_DIR, DEFAULT_ACOUSTIC_MODEL)
    )
    asr_config["hmm"] = acoustic_model
    if alignment_mode == "strict":
        asr_config["beam"] = 1e-100
        asr_config["pbeam"] = 1e-100
        asr_config["wbeam"] = 1e-80
    elif alignment_mode == "moderate":
        asr_config["beam"] = 1e-200
        asr_config["pbeam"] = 1e-200
        asr_config["wbeam"] = 1e-160
    elif alignment_mode == "loose":
        asr_config["beam"] = 0
        asr_config["pbeam"] = 0
        asr_config["wbeam"] = 0
    else:
        assert False and "invalid alignment_mode value"

    if debug_aligner:
        # With --debug-aligner, we display the SoundSwallower logs on
        # screen and set them to maximum strength
        asr_config["loglevel"] = "DEBUG"
    else:
        # Otherwise, we enable logging and direct it to a file if
        # saving temporary files
        if save_temps is not None and (sys.platform not in ("win32", "cygwin")):
            # With --save-temps, we save the SoundSwallower logs to a file.
            # This is buggy on Windows, so we don't do it on Windows variants
            # (NOTE: should be fixed in SoundSwallower 0.3 though)
            ss_log = save_temps + ".soundswallower.log"
            asr_config["logfn"] = ss_log
            asr_config["loglevel"] = "INFO"
        # And otherwise the default is fine (only error messages are printed)

    # Set sampling rate based on audio (FIXME: this may cause problems
    # later on if it is too low)
    asr_config["samprate"] = audio.frame_rate
    # Set the minimum FFT size (no longer necessary since
    # SoundSwallower 0.2, but we keep this here for compatibility with
    # old versions in case we need to debug things)
    frame_points = int(asr_config["samprate"] * asr_config["wlen"])  # type: ignore
    fft_size = 1
    while fft_size < frame_points:
        fft_size = fft_size << 1
    asr_config["nfft"] = fft_size

    # Disable VAD
    asr_config["remove_noise"] = False

    return asr_config


def read_noisedict(asr_config: soundswallower.Config) -> Set[str]:
    """Read the list of noise words from the acoustic model.

    Args:
        asr_config (soundswallower.Config): ASR configuration.
    Returns:
        Set[str]: Set of noise words from noisedict, or a default set
            if it could not be found.
    """

    def load_noisedict(fdict):
        try:
            with open(fdict, "rt", encoding="utf-8") as dictfh:
                noisewords = set()
                for line in dictfh:
                    if line.startswith("##") or line.startswith(";;"):
                        continue
                    noisewords.add(line.strip().split()[0])
                return noisewords
        except FileNotFoundError:
            return None

    fdict: str = asr_config["fdict"]  # type: ignore
    acoustic_model: str = asr_config["hmm"]  # type: ignore
    noisewords = None
    if fdict is not None:  # pragma: no cover
        noisewords = load_noisedict(fdict)
    if noisewords is None:
        noisewords = load_noisedict(os.path.join(acoustic_model, "noisedict.txt"))
    if noisewords is None:  # pragma: no cover
        noisewords = load_noisedict(os.path.join(acoustic_model, "noisedict"))
    if noisewords is None:  # pragma: no cover
        LOGGER.warning("Could not find noisedict, using defaults")
        noisewords = {"<sil>", "<s>", "</s>", "[NOISE]"}

    return noisewords


def process_dna(
    dna_config: Dict[str, Any],
    audio: AudioSegment,
    audio_path: Optional[str] = None,
    save_temps: Optional[str] = None,
) -> Tuple[AudioSegment, List[dict], List[dict]]:
    """Apply do-not-align processing to audio.

    Args:
        dna_config (dict): Do-not-align configuration, containing at least "segments" and "method".
        audio (AudioSegment): Original audio segment.
        audio_path (str): Optional; Path from which audio was loaded (needed for save_temps).
        save_temps (str): Optional; Prefix for saving temporary files, by default None.

    Returns:
        Tuple[AudioSegment, List[dict], List[dict]]: Processed audio
            segment, list of segments marked do-not-align, list of segments
            actually removed.
    """
    # Sort un-alignable segments and join overlapping ones
    dna_segments = sort_and_join_dna_segments(dna_config["segments"])
    method = dna_config.get("method", "remove")
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
        for dna_seg in reversed(dna_segments):
            processed_audio = dna_method(
                processed_audio, int(dna_seg["begin"]), int(dna_seg["end"])
            )
        if save_temps is not None:
            assert audio_path is not None
            _, ext = os.path.splitext(audio_path)
            try:
                processed_audio.export(save_temps + "_processed" + ext, format=ext[1:])
            except CouldntEncodeError:
                try:
                    os.remove(save_temps + "_processed" + ext)
                except BaseException:  # Ignore Windows file removal failures
                    pass
                LOGGER.warning(
                    f"Couldn't find encoder for '{ext[1:]}', defaulting to 'wav'"
                )
                processed_audio.export(save_temps + "_processed" + ".wav")
        removed_segments = dna_segments
    return processed_audio, dna_segments, removed_segments


def align_sequence(
    audio_data: AudioSegment,
    word_sequence: WordSequence,
    asr_config: soundswallower.Config,
    xml_path: str,
    i: int,
    unit: Optional[str] = "w",
    save_temps: Optional[str] = None,
) -> AudioSegment:
    """Run alignment for a word sequence.

    Args:
        audio_data (AudioSegment): Full input audio.
        word_sequence (WordSequence): Sequence of units to align.
        asr_config (soundswallower.Config): Aligner configuration.
        unit (str): Name of unit we are aligning.
        xml_path (str): Path to input XML file.
        i (int): Index of this sequence in the full file.

        save_temps (str): Optional; Prefix for saving temporary files,
            or None to not save them.

    Returns:
        Iterable[soundswallower.Seg]: Word (or other unit) alignments.

    Raises:
        RuntimeError: If alignment fails (TODO: figure out why).
    """
    i_suffix = "" if i == 0 else "." + str(i + 1)

    # Generate dictionary and FSG for the current sequence of words
    dict_data = make_dict(word_sequence.words, xml_path, unit=unit)
    if save_temps is not None:
        dict_file = io.open(save_temps + ".dict" + i_suffix, "wb")
    else:
        dict_file = PortableNamedTemporaryFile(prefix="readalongs_dict_", delete=True)
    dict_file.write(dict_data.encode("utf-8"))
    dict_file.close()

    fsg_data = make_fsg(word_sequence.words, xml_path)
    if save_temps is not None:
        fsg_file = io.open(save_temps + ".fsg" + i_suffix, "wb")
    else:
        fsg_file = PortableNamedTemporaryFile(prefix="readalongs_fsg_", delete=True)
    fsg_file.write(fsg_data.encode("utf-8"))
    fsg_file.close()

    # Extract the part of the audio corresponding to this word sequence
    audio_segment = extract_section(audio_data, word_sequence.start, word_sequence.end)
    if save_temps is not None and audio_segment is not audio_data:
        write_audio_to_file(audio_segment, save_temps + ".wav" + i_suffix)

    # Configure soundswallower for this sequence's dict and fsg
    asr_config["dict"] = dict_file.name
    asr_config["fsg"] = fsg_file.name

    ps = soundswallower.Decoder(asr_config)
    # Align this word sequence
    ps.start_utt()
    ps.process_raw(audio_segment.raw_data, no_search=False, full_utt=True)
    ps.end_utt()

    return ps.seg


def process_segmentation(
    segmentation: Iterable[soundswallower.Seg],
    curr_removed_segments: List[dict],
    noisewords: Set[str],
    frame_size: float,
    debug_aligner: Optional[bool] = False,
) -> List[Dict[str, Any]]:
    """Correct output alignments based on do-not-align segments."""
    aligned_words: List[Dict[str, Any]] = []
    for word_seg in segmentation:
        if word_seg.text in noisewords:
            continue
        start = word_seg.start
        end = word_seg.start + word_seg.duration
        # round to milliseconds to avoid imprecisions
        start_ms = round(start * 1000)
        end_ms = round(end * 1000)
        # possibly adjust for removed sections
        if curr_removed_segments:
            start_ms += calculate_adjustment(start_ms, curr_removed_segments)
            end_ms += calculate_adjustment(end_ms, curr_removed_segments)
            start_ms, end_ms = correct_adjustments(
                start_ms, end_ms, curr_removed_segments
            )
        # change back to seconds
        start = start_ms / 1000
        end = end_ms / 1000
        if aligned_words:
            assert start >= aligned_words[-1]["end"]
        aligned_words.append({"id": word_seg.text, "start": start, "end": end})
        if debug_aligner:
            LOGGER.info("Segment: %s (%.3f : %.3f)", word_seg.text, start, end)
    return aligned_words


def insert_silence(
    results: Dict[str, Any],
    audio: AudioSegment,
    xml_path: Optional[str] = "XML Input",
):
    """Insert the required silences in the audio stream."""
    words_dict = {
        x["id"]: {"start": x["start"], "end": x["end"]} for x in results["words"]
    }
    silence_offsets: defaultdict = defaultdict(int)
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


def add_alignments(
    results: Dict[str, Any],
):
    """Add the computed alignments to the XML tags."""
    # Round all times to three digits, as noted below
    words_dict = {
        x["id"]: (("%.3f" % x["start"]), ("%.3f" % (x["end"] - x["start"])))
        for x in results["words"]
    }
    # FIXME: Should propagate durations to higher-level elements, ideally
    for el in results["tokenized"].xpath("//w"):
        # It may not be aligned
        if el.attrib["id"] in words_dict:
            el.attrib["time"], el.attrib["dur"] = words_dict[el.attrib["id"]]


def align_audio(
    xml_path: str,
    audio_path: str,
    *,  # force the remaining arguments to be passed by name
    unit: Optional[str] = "w",
    bare: Optional[bool] = False,
    config: Optional[dict] = None,
    save_temps: Optional[str] = None,
    verbose_g2p_warnings: Optional[bool] = False,
    debug_aligner: Optional[bool] = False,
    output_orthography: str = "eng-arpabet",
    alignment_mode: str = "auto",
):
    """Align an XML input file to an audio file.

    Args:
        xml_path (str): Path to input file in ReadAlong XML format (see static/read-along-1.2.dtd)
        audio_path (str): Path to audio input. Must be in a format supported by ffmpeg
        unit (str): Optional; Element to create alignments for, by default 'w'
        bare (boolean): Optional;
            If False, split silence into adjoining tokens (default)
            If True, keep the bare tokens without adjoining silences.
        config (dict): Optional; ReadAlong-Studio configuration to use
        save_temps (str): Optional; Prefix for saving temporary files, or None if
            temporary files are not to be saved.
        verbose_g2p_warnings (boolean): Optional; display all g2p errors and warnings
            iff True
        debug_aligner (boolean): Optional, output debugging info from the aligner.
        alignment_mode (str): Optional, controls the decoder beam width

    Returns:
        Dict[str, Any]: TODO

    Raises:
        TODO
    """
    results: Dict[str, Any] = {"words": [], "audio": None}
    if config is None:
        config = {}

    xml = parse_and_make_xml(
        xml_path=xml_path,
        config=config,
        verbose_g2p_warnings=verbose_g2p_warnings,
        save_temps=save_temps,
        output_orthography=output_orthography,
    )
    results["tokenized"] = xml

    # Read the audio file
    audio = read_audio_from_file(audio_path)
    audio = audio.set_channels(1).set_sample_width(2)
    audio_length_in_ms = len(audio.raw_data)

    # Expand the list of alignment modes to try
    if alignment_mode == "auto":
        align_modes = ["strict", "moderate", "loose"]
    else:
        align_modes = [alignment_mode]

    # Create the ASR configuration for each alignment mode needed
    asr_configs = [
        create_asr_config(config, audio, save_temps, debug_aligner, align_mode)
        for align_mode in align_modes
    ]
    asr_config = asr_configs[0]  # Default/first ASR Config

    # Process audio, silencing or removing any DNA segments
    if "do-not-align" in config:
        audio_data, dna_segments, removed_segments = process_dna(
            dna_config=config["do-not-align"],
            audio=audio,
            audio_path=audio_path,
            save_temps=save_temps,
        )
    else:
        audio_data = audio
        dna_segments = []
        removed_segments = []

    # Note: the frames are typically 0.01s long (i.e., the frame rate is typically 100),
    # while the audio segments manipulated using pydub are sliced and accessed in
    # millisecond intervals. For audio segments, the ms slice assumption is hard-coded
    # all over, while frame_size is used to convert segment boundaries returned by
    # soundswallower, which are indexes in frames, into durations in seconds.
    frame_size = 1.0 / asr_config["frate"]  # type: ignore

    # Get list of words to ignore in aligner output
    noisewords = read_noisedict(asr_config)

    # Extract the list of sequences of words in the XML
    word_sequences = get_sequences(xml, xml_path, unit=unit)
    final_end = 0.0
    for i, word_sequence in enumerate(word_sequences):
        for j, cur_asr_config in enumerate(asr_configs):
            # Run the aligner on this sequence
            segmentation = align_sequence(
                audio_data=audio_data,
                word_sequence=word_sequence,
                asr_config=cur_asr_config,
                xml_path=xml_path,
                i=i,
                unit=unit,
                save_temps=save_temps,
            )

            # List of removed segments for the sequence we are currently processing
            curr_removed_segments = dna_union(
                word_sequence.start,
                word_sequence.end,
                audio_length_in_ms,
                removed_segments,
            )
            # Process raw segmentation, adjusting alignments for DNA
            aligned_words = process_segmentation(
                segmentation=segmentation,
                curr_removed_segments=curr_removed_segments,
                noisewords=noisewords,
                frame_size=frame_size,
                debug_aligner=debug_aligner,
            )

            if len(aligned_words) != len(word_sequence.words):
                LOGGER.warning(f"Align mode {align_modes[j]} failed for sequence {i}.")
            else:
                LOGGER.info(f"Align mode {align_modes[j]} succeeded for sequence {i}.")
                break

        results["words"].extend(aligned_words)
        if aligned_words:
            final_end = aligned_words[-1]["end"]
        if len(aligned_words) != len(word_sequence.words):
            LOGGER.warning(
                f"Word sequence {i + 1} had {len(word_sequence.words)} tokens "
                f"but produced {len(aligned_words)} segments. "
                "Check that the anchors are well positioned or "
                "that the audio corresponds to the text."
            )

    aligned_segment_count = len(results["words"])
    token_count = len(results["tokenized"].xpath(f"//{unit}"))
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

    # Split silences if requested
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

    # Insert silences if requested
    insert_silence(
        results=results,
        audio=audio,
        xml_path=xml_path,
    )

    # Add alignments to word tags
    add_alignments(
        results=results,
    )

    return results


def get_audio_duration(audiofile: str) -> float:
    """Return the duration of audiofile in seconds"""
    audio = read_audio_from_file(audiofile)
    return audio.frame_count() / audio.frame_rate


def save_label_files(
    words: List[dict],
    tokenized_xml: etree.ElementTree,
    duration: float,
    output_base: str,
    output_formats: Iterable[str],
):
    """Save label (TextGrid and/or EAF) files.

    Args:
        words: list of words with "id", "start" and "end"
        tokenized_xml: tokenized or g2p'd parsed XML object
        duration: length of the audio in seconds
        output_base (str): Base path for output files
        output_formats (Iterable[str]): List of output formats

    Raises:
        IndexError: words and tokenized_xml have inconsistent IDs
        Exception: TODO, not sure what else this can raise
    """
    words_with_text, sentences = get_word_texts_and_sentences(words, tokenized_xml)
    textgrid = create_text_grid(words_with_text, sentences, duration)

    if "textgrid" in output_formats:
        textgrid.to_file(output_base + ".TextGrid")

    if "eaf" in output_formats:
        textgrid.to_eaf().to_file(output_base + ".eaf")


def save_subtitles(
    words: List[dict],
    tokenized_xml: etree.ElementTree,
    output_base: str,
    output_formats=Iterable[str],
):
    """Save subtitle (SRT and/or VTT) files.

    Args:
        words: list of words with "id", "start" and "end"
        tokenized_xml: tokenized or g2p'd parsed XML object
        output_base (str): Base path for output files
        output_formats (Iterable[str]): List of output formats

    Raises:
        IndexError: words and tokenized_xml have inconsistent IDs
        Exception: TODO, not sure what else this can raise
    """
    words_with_text, sentences = get_word_texts_and_sentences(words, tokenized_xml)
    cc_sentences = write_to_subtitles(sentences)
    cc_words = write_to_subtitles(words_with_text)

    if "srt" in output_formats:
        cc_sentences.save_as_srt(output_base + "_sentences.srt")
        cc_words.save_as_srt(output_base + "_words.srt")

    if "vtt" in output_formats:
        cc_words.save(output_base + "_words.vtt")
        cc_sentences.save(output_base + "_sentences.vtt")


def save_audio(
    audiofile: str, output_base: str, audiosegment: Optional[AudioSegment] = None
) -> str:
    """Save audio file.

    Args:
        audiofile (str): Path to input audio
        output_base (str): Base path for output files
        output_formats (Iterable[str]): List of output formats
        audiosegment (AudioSegment): Optional; trimmed/muted audio
    Returns:
        str: Path to output audio file.
    """
    _, audio_ext = os.path.splitext(audiofile)
    audio_path = output_base + audio_ext
    audio_format = audio_ext[1:]
    if audiosegment is not None:
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
    return audio_path


def save_images(config: Dict[str, Any], output_dir: str):
    """Save image files specified in config.

    Args:
        config (dict): ReadAlong-Studio configuration
        output_dir (str): Output directory
    Raises:
        FileExistsError: If output directory already exists
    """
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


def save_readalong(
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
        save_label_files(
            words=align_results["words"],
            tokenized_xml=align_results["tokenized"],
            duration=get_audio_duration(audiofile),
            output_base=output_base,
            output_formats=output_formats,
        )

    # Create webvtt object if outputting to vtt or srt
    if "srt" in output_formats or "vtt" in output_formats:
        save_subtitles(
            words=align_results["words"],
            tokenized_xml=align_results["tokenized"],
            output_base=output_base,
            output_formats=output_formats,
        )

    bundle_path = os.path.join(output_dir, "www")
    if not os.path.exists(bundle_path):
        os.mkdir(bundle_path)
    bundle_base = os.path.join(bundle_path, output_basename)

    ras_path = bundle_base + ".readalong"
    save_xml(ras_path, align_results["tokenized"])

    if "xhtml" in output_formats:
        convert_to_xhtml(align_results["tokenized"])
        tokenized_xhtml_path = output_base + ".xhtml"
        save_xml(tokenized_xhtml_path, align_results["tokenized"])

    audio_path = save_audio(
        audiofile=audiofile, output_base=bundle_base, audiosegment=audiosegment
    )

    if "html" in output_formats:
        offline_html_dir = os.path.join(output_dir, "Offline-HTML")
        html_out_path = os.path.join(offline_html_dir, output_basename + ".html")
        html_out = create_web_component_html(
            ras_path,
            audio_path,
            config.get("title", DEFAULT_TITLE),
            config.get("header", DEFAULT_HEADER),
            config.get("subheader", DEFAULT_SUBHEADER),
            config.get("theme", "light"),
        )
        if not os.path.exists(offline_html_dir):
            os.mkdir(offline_html_dir)
        with open(html_out_path, "w", encoding="utf-8") as f:
            f.write(html_out)

    save_minimal_index_html(
        os.path.join(bundle_path, "index.html"),
        os.path.basename(ras_path),
        os.path.basename(audio_path),
        config.get("title", DEFAULT_TITLE),
        config.get("header", DEFAULT_HEADER),
        config.get("subheader", DEFAULT_SUBHEADER),
        config.get("theme", "light"),
    )

    # Copy the image files to the output's asset directory, if any are found
    if "images" in config:
        save_images(config=config, output_dir=bundle_path)
    save_readme_txt(
        os.path.join(bundle_path, "readme.txt"),
        os.path.basename(ras_path),
        os.path.basename(audio_path),
        config.get("header", DEFAULT_HEADER),
        config.get("subheader", DEFAULT_SUBHEADER),
        config.get("theme", "light"),
    )


def get_word_element(xml: etree.ElementTree, el_id: str) -> etree.ElementTree:
    """Get the xml etree for a given word by its id"""
    return xml.xpath(f'//w[@id="{el_id}"]')[0]


def get_ancestor_sent_el(word_el: etree.ElementTree) -> Union[None, etree.ElementTree]:
    """Get the ancestor <s> node for word_el, or None"""
    while word_el is not None and word_el.tag != "s":
        word_el = word_el.getparent()
    return word_el


def get_word_texts_and_sentences(
    words: List[dict], tokenized_xml: etree.ElementTree
) -> Tuple[List[dict], List[List[dict]]]:
    """Parse xml into word and sentence 'tier' data with full textual words

    Args:
        words: list of words with "id", "start" and "end"
        tokenized_xml: tokenized or g2p'd parsed XML object

    Returns:
        list of words, list of sentences (as a list of lists of words)
        The returned words are dicts containing:
           "text": the actual textual word from the XML (not the ID)
           "start": start time
           "end": end time
    """
    sentences = []
    sent_words: List[Dict[str, Any]] = []
    all_words: List[Dict[str, Any]] = []
    prev_sent_el = None
    for word in words:
        # The sentence is considered the set of words under the same <s> element.
        # A word that's not under any <s> element is bad input, but we consider
        # it a sentence by itself for software robustness.
        word_el = get_word_element(tokenized_xml, word["id"])
        sent_el = get_ancestor_sent_el(word_el)
        if prev_sent_el is None or sent_el is not prev_sent_el:
            if sent_words:
                sentences.append(sent_words)
            sent_words = []
            prev_sent_el = sent_el
        word_with_text = {
            "text": get_word_text(word_el),
            "start": word["start"],
            "end": word["end"],
        }
        if all_words:
            assert word_with_text["start"] >= all_words[-1]["end"]
        sent_words.append(word_with_text)
        all_words.append(word_with_text)
    if sent_words:
        sentences.append(sent_words)
    return all_words, sentences


def create_text_grid(
    words: List[dict], sentences: List[List[dict]], duration: float
) -> TextGrid:
    """Create Praat TextGrid from results. Because we are using pympi, we can also export to Elan EAF.

    Args:
        words (List[dict]): List of words containing "text", "start", "end"
        sentences (List[dict]): List of sentences (as a list of lists of word dicts)
        duration (float): duration of entire audio

    Returns:
        TextGrid: Praat TextGrid object with word and sentence alignments
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
    # The read-along version ends up as html version, which makes no sense, so remove it
    if "version" in tokenized_xml.attrib:
        del tokenized_xml.attrib["version"]
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


# TODO: add this <!-- DO NOT USE THIS DATA WITHOUT EXPLICIT PERMISSION --> to template
RAS_TEMPLATE = """<?xml version='1.0' encoding='utf-8'?>
<read-along version="{{format_version}}">
    <meta name="generator" content="@readalongs/studio (cli) {{studio_version}}" />
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
</read-along>
"""


def create_ras_from_text(lines: Iterable[str], text_languages=Sequence[str]) -> str:
    """Create input xml in ReadAlong XML format (see static/read-along-1.2.dtd)
        Uses the line sequence to infer paragraph and sentence structure from plain text:
        Assumes a double blank line marks a page break, and a single blank line
        marks a paragraph break.
        Creates the XML using chevron

    Args:
        lines: lines from the input plain text, e.g., f.readlines() on file handle f
        text_languages: non-empty list of languages for g2p conversion

    Returns:
        str: Formatted XML, ready to print
    """
    assert text_languages, "The text_languages list may not be empty."
    kwargs = {
        "main_lang": text_languages[0],
        "fallback_langs": ",".join(text_languages[1:]),
        "studio_version": VERSION,
        "format_version": READALONG_FILE_FORMAT_VERSION,
    }
    pages: List[dict] = []
    paragraphs: List[dict] = []
    sentences: List[str] = []
    for line in lines:
        stripped_line = line.strip()
        if stripped_line == "":
            if not sentences:
                # The previous line was also blank, so this is a page break
                # (but don't insert empty pages)
                if paragraphs:
                    pages.append({"paragraphs": paragraphs})
                paragraphs = []
            else:
                # add sentences and begin new paragraph
                paragraphs.append({"sentences": sentences})
                sentences = []
        else:
            # Add text to sentence
            sentences.append(stripped_line)
    # Add the last paragraph/sentence
    if sentences:
        paragraphs.append({"sentences": sentences})
    if paragraphs:
        pages.append({"paragraphs": paragraphs})
    return chevron.render(RAS_TEMPLATE, {**kwargs, **{"pages": pages}})


def create_input_ras(**kwargs):
    """Create input xml in ReadAlong XML format (see static/read-along-1.2.dtd)
        Uses readlines to infer paragraph and sentence structure from plain text.
        Assumes a double blank line marks a page break, and a single blank line
        marks a paragraph break.
        Outputs to uft-8 XML using chevron.

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
            with io.open(kwargs["input_file_name"], encoding="utf-8-sig") as f:
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

    save_temps = kwargs.get("save_temps", None)
    if kwargs.get("output_file", False):
        filename = kwargs.get("output_file")
        outfile = io.open(filename, "wb")
    elif save_temps is not None:
        filename = save_temps + ".input.readalong"
        outfile = io.open(filename, "wb")
    else:
        outfile = PortableNamedTemporaryFile(
            prefix="readalongs_xml_", suffix=".readalong", delete=True
        )
        filename = outfile.name
    xml = create_ras_from_text(text, text_langs)
    outfile.write(xml.encode("utf-8"))
    outfile.flush()
    outfile.close()
    return outfile, filename
