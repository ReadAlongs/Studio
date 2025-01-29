"""
Functions for saving alignments in various file formats.
"""

import io
from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import chevron
from lxml import etree
from pympi.Praat import TextGrid
from webvtt import Caption, WebVTT

from readalongs._version import READALONG_FILE_FORMAT_VERSION, VERSION
from readalongs.portable_tempfile import PortableNamedTemporaryFile
from readalongs.text.add_elements_to_xml import add_images, add_supplementary_xml
from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.convert_xml import convert_xml
from readalongs.text.tokenize_xml import tokenize_xml
from readalongs.text.util import get_word_text, load_xml, save_xml


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


def create_ras_from_text(lines: Iterable[str], text_languages: Sequence[str]) -> str:
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
