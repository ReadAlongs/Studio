"""
make_smil.py

Turns alignment into formatted SMIL for ReadAlongs WebComponent
"""

from typing import List

import chevron
from lxml import etree

from readalongs.text.util import parse_xml

SMIL_TEMPLATE = """\
<smil xmlns="http://www.w3.org/ns/SMIL" version="3.0">
    <body>
        {{#words}}
        <par id="par-{{id}}">
            <text src="{{text_path}}#{{id}}"/>
            <audio src="{{audio_path}}" clipBegin="{{start}}" clipEnd="{{end}}"/>
        </par>
        {{/words}}
    </body>
</smil>
"""

BASENAME_IDX = 0
START_TIME_IDX = 9
WORDS_IDX = 10
WORD_SPAN = 4
WORD_SUBIDX = 2
END_SUBIDX = 3


def make_smil(text_path: str, audio_path: str, words: List[dict]) -> str:
    """Actually render the SMIL

    words is a list of dicts with these elements:
    {
        "id": word id (str),
        "start": word start time in seconds (float),
        "end": word_end_time_in_seconds (float),
    }

    Args:
        text_path (str): path to text
        audio_path (str): path to audio
        words (List[dict]): all alignments

    Returns:
        str: formatted SMIL
    """
    return chevron.render(
        SMIL_TEMPLATE,
        {"text_path": text_path, "audio_path": audio_path, "words": words},
    )


def parse_smil(formatted_smil: str) -> List[dict]:
    """Extract the list of words and their alignment from a SMIL file content.

    Args:
        formatted_smil (str): the raw, unparsed XML content of the .smil file

    Returns:
        List[dict]: a list of dicts with these elements:
            {
                "id": word id (str),
                "start": word start time in seconds (float),
                "end": word_end_time_in_seconds (float),
            }
    Raises:
        ValueError if there is a problem parsing formatted_smil as valid SMIL
    """

    please_msg = "Please make sure your SMIL file is valid."

    try:
        xml = parse_xml(formatted_smil)
    except etree.ParseError as e:
        raise ValueError(f"Invalid SMIL file: {e}. {please_msg}")
    ns = {"smil": "http://www.w3.org/ns/SMIL"}

    words = []
    for par_el in xml.xpath(".//smil:par", namespaces=ns):
        text_src = par_el.find("smil:text", namespaces=ns).attrib["src"]
        _, _, text_id = text_src.partition("#")
        if not text_id:
            raise ValueError(f"Missing word id. {please_msg}")
        audio_el = par_el.find("smil:audio", namespaces=ns)
        try:
            clip_begin = float(audio_el.attrib["clipBegin"])
            clip_end = float(audio_el.attrib["clipEnd"])
        except KeyError as e:
            raise ValueError(f"Missing 'clipBegin' or 'clipEnd'. {please_msg}") from e
        except ValueError as e:
            raise ValueError(
                f"Invalid 'clipBegin' or 'clipEnd': {e}. {please_msg}."
            ) from e

        words.append({"id": text_id, "start": clip_begin, "end": clip_end})

    return words
