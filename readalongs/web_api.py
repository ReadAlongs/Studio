"""
REST-ish Web API for ReadAlongs Studio text manipulation operations using FastAPI.

See https://readalong-studio.herokuapp.com/api/v1/docs for the documentation.

You can spin up this Web API for development purposes with:
    cd readalongs/
    PRODUCTION= uvicorn readalongs.web_api:web_api_app --reload
- The --reload switch will watch for changes under the directory where it's
  running and reload the code whenever it changes, so it's best run in readalongs/
- PRODUCTION= tells uvicorn to run in non-production mode, i.e., in debug mode,
  and automatically add the header "access-control-allow-origin: *" to each
  response so you won't get CORS errors using this locally with Studio-Web.

You can also spin up the API server grade (on Linux, not Windows) with gunicorn:
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker readalongs.web_api:web_api_app

Once spun up, the documentation and API playground will be visible at
http://localhost:8000/api/v1/docs
"""

import io
import os
import tempfile
from enum import Enum
from textwrap import dedent
from typing import Dict, List, Optional, Union

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from lxml import etree
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from readalongs.align import create_tei_from_text, save_label_files, save_subtitles
from readalongs.log import LOGGER
from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.convert_xml import convert_xml
from readalongs.text.make_dict import make_dict_object
from readalongs.text.make_fsg import make_jsgf
from readalongs.text.make_smil import parse_smil
from readalongs.text.tokenize_xml import tokenize_xml
from readalongs.util import get_langs

# Create the app
web_api_app = FastAPI()
# Create the v1 version of the API
v1 = FastAPI()
# Call get_langs() when the server loads to load the languages into memory
LANGS = get_langs()

if os.getenv("PRODUCTION", True):
    origins = [
        "https://readalong-studio.mothertongues.org",
    ]  # Allow requests from mt app
else:
    origins = ["*"]  # Allow requests from any origin
web_api_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class RequestBase(BaseModel):
    """Base request for assemble"""

    text_languages: List[str]
    debug: bool = False


class PlainTextRequest(RequestBase):
    """Request to assemble with input as plain text"""

    text: str


class XMLRequest(RequestBase):
    """Request to assemble with input as XML"""

    xml: str


class AssembleResponse(BaseModel):
    """Response from assemble with the XML prepared and the rest."""

    lexicon: Dict[str, str]  # A dictionary of the form {lang_id: lang_name }
    jsgf: str  # The JSGF-formatted grammar in plain text
    text_ids: str  # The text ID input for the decoder in plain text
    processed_xml: str  # The processed XML is returned as a string
    input: Optional[Union[XMLRequest, PlainTextRequest]]
    parsed: Optional[str]
    tokenized: Optional[str]
    g2ped: Optional[str]


@v1.get("/langs", response_model=Dict[str, str])
async def langs() -> Dict[str, str]:
    """Return the list of supported languages and their names as a dict.

    Returns:
        langs as dict with language codes as keys and the full language name as
        values, e.g.:
        `{
            "alq", "Algonquin",
            "atj": "Atikamekw",
            "lc3", "Third Language Name",
            ...
        }`
    """

    return LANGS[1]


@v1.post("/assemble", response_model=AssembleResponse)
async def assemble(
    request: Union[XMLRequest, PlainTextRequest] = Body(
        examples={
            "text": {
                "summary": "A basic example with plain text input",
                "value": {
                    "text": "hej verden",
                    "text_languages": ["dan", "und"],
                    "debug": False,
                },
            },
            "xml": {
                "summary": "A basic example with xml input",
                "value": {
                    "xml": "<?xml version='1.0' encoding='utf-8'?><TEI><text><p><s>hej verden</s></p></text></TEI>",
                    "text_languages": ["dan", "und"],
                    "debug": False,
                },
            },
        }
    )
):
    """Create an input TEI from the given text (as plain text or XML).
    Also creates the required grammar, pronunciation dictionary,
    and text needed by the decoder.

    Encoding: all input and output is in UTF-8.

    Args (as dict items in the request body):
     - text_languages: the list of languages for g2p processing
     - debug: set to true for debugging (default: False)
     - either text or xml:
        - text: the input text as plain text
        - xml: the input text as a readalongs-compatible XML structure

    Returns (as dict items in the response body):
     - lexicon: maps word IDs to their pronunciation
     - jsgf: grammar for the forced aligner
     - text_ids: the list of word_ids as a space-separated string
     - processed_xml: the XML with all the readalongs info in it
    """

    if isinstance(request, XMLRequest):
        try:
            parsed = etree.fromstring(
                bytes(request.xml, encoding="utf-8"),
                parser=etree.XMLParser(resolve_entities=False),
            )
        except etree.XMLSyntaxError as e:
            raise HTTPException(
                status_code=422, detail="XML provided is not valid"
            ) from e
    elif isinstance(request, PlainTextRequest):
        parsed = io.StringIO(request.text).readlines()
        parsed = etree.fromstring(
            bytes(
                create_tei_from_text(parsed, text_languages=request.text_languages),
                encoding="utf-8",
            ),
            parser=etree.XMLParser(resolve_entities=False),
        )
    # tokenize
    tokenized = tokenize_xml(parsed)
    # add ids
    ids_added = add_ids(tokenized)
    # g2p
    g2ped, valid = convert_xml(ids_added)
    if not valid:
        raise HTTPException(
            status_code=422,
            detail="g2p could not be performed, please check your text or your language code",
        )
    # create grammar
    dict_data, jsgf, text_input = create_grammar(g2ped)
    response = {
        "lexicon": dict_data,
        "jsgf": jsgf,
        "text_ids": text_input,
        "processed_xml": etree.tostring(g2ped, encoding="utf8").decode(),
    }

    if request.debug:
        response["input"] = request.dict()
        response["parsed"] = etree.tostring(parsed, encoding="utf8")
        response["tokenized"] = etree.tostring(tokenized, encoding="utf8")
        response["g2ped"] = etree.tostring(g2ped, encoding="utf8")
    return response


def create_grammar(xml):
    """Create the grammar and dictionary data from w elements in the given XML"""

    word_elements = xml.xpath("//w")
    dict_data = make_dict_object(word_elements)
    fsg_data = make_jsgf(word_elements, filename="test")
    text_data = " ".join(xml.xpath("//w/@id"))
    return dict_data, fsg_data, text_data


class FormatName(Enum):
    """The different formats supported to represent readalong alignments"""

    TEXTGRID = "textgrid"  # Praat TextGrid format
    EAF = "eaf"  # ELAN EAF format
    SRT = "srt"  # SRT subtitle format
    VTT = "vtt"  # VTT subtitle format


class ConvertRequest(BaseModel):
    """Convert Request contains the RAS-processed XML and SMIL alignments"""

    audio_duration: float = Field(
        example=2.01,
        gt=0.0,
        title="The duration of the audio used to create the alignment, in seconds.",
    )

    xml: str = Field(
        title="The processed_xml returned by /assemble.",
        example=dedent(
            """\
            <?xml version='1.0' encoding='utf-8'?>
            <TEI>
                <text xml:lang="dan" fallback-langs="und" id="t0">
                    <body id="t0b0">
                        <div type="page" id="t0b0d0">
                            <p id="t0b0d0p0">
                                <s id="t0b0d0p0s0"><w id="t0b0d0p0s0w0" ARPABET="HH EH Y">hej</w> <w id="t0b0d0p0s0w1" ARPABET="V Y D EH N">verden</w></s>
                            </p>
                        </div>
                    </body>
                </text>
            </TEI>"""
        ),
    )

    smil: str = Field(
        title="The result of aligning xml to the audio with SoundSwallower(.js)",
        example=dedent(
            """\
            <smil xmlns="http://www.w3.org/ns/SMIL" version="3.0">
                <body>
                    <par id="par-t0b0d0p0s0w0">
                        <text src="hej-verden.xml#t0b0d0p0s0w0"/>
                        <audio src="hej-verden.mp3" clipBegin="0.14" clipEnd="0.78"/>
                    </par>
                    <par id="par-t0b0d0p0s0w1">
                        <text src="hej-verden.xml#t0b0d0p0s0w1"/>
                        <audio src="hej-verden.mp3" clipBegin="0.78" clipEnd="1.89"/>
                    </par>
                </body>
            </smil>"""
        ),
    )


class SubtitleTier(Enum):
    """Which tier of the alignment information is returned"""

    SENTENCE = "sentence"
    WORD = "word"


@v1.post("/convert_alignment/{output_format}")
async def convert_alignment(  # noqa: C901
    request: ConvertRequest,
    output_format: FormatName,
    tier: Union[SubtitleTier, None] = None,
) -> FileResponse:
    """Convert an alignment to a different format.

    Encoding: all input and output is in UTF-8.

    Path Parameter:
     - output_format: Format to convert to, one of textgrid (Praat TextGrid),
       eaf (ELAN EAF), srt (SRT subtitles), or vtt (VTT subtitles).

    Query Parameter:
     - tier: for srt and vtt outputs, whether the subtitles should be at the
       sentence (this is the default) or word level.

    Args (as dict items in the request body):
     - audio_duration: duration in seconds of the audio file used to create the alignment
     - xml: the XML file produced by /assemble
     - smil: the SMIL file produced by SoundSwallower(.js)

    Formats supported:
     - TextGrid: Praat TextGrid file format
     - eaf: ELAN eaf file format
     - srt: SRT subtitle format (at the sentence or word level, based on tier)
     - vtt: WebVTT subtitle format (at the sentence or word level, based on tier)

    Data privacy consideration: due to limitations of the libraries used to perform
    some of these conversions, the output files will be temporarily stored on disk,
    but they get deleted immediately as this endpoint returns its output or reports
    any error.

    Returns: a file in the format requested
    """
    try:
        parsed_xml = etree.fromstring(
            bytes(request.xml, encoding="utf-8"),
            parser=etree.XMLParser(resolve_entities=False),
        )
    except etree.XMLSyntaxError as e:
        raise HTTPException(status_code=422, detail="XML provided is not valid") from e

    try:
        words = parse_smil(request.smil)
    except ValueError as e:
        raise HTTPException(status_code=422, detail="SMIL provided is not valid") from e

    # Data privacy consideration: we have to make sure this temporary directory gets
    # deleted after the call returns, as we promise in the API documentation.
    temp_dir_object = tempfile.TemporaryDirectory()
    temp_dir_name = temp_dir_object.name
    cleanup = BackgroundTask(temp_dir_object.cleanup)
    prefix = os.path.join(temp_dir_name, "aligned")
    LOGGER.info("Temporary directory: %s", temp_dir_name)

    try:
        if output_format == FormatName.TEXTGRID:
            try:
                save_label_files(
                    words, parsed_xml, request.audio_duration, prefix, "textgrid"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail="XML+SMIL file pair provided cannot be converted",
                ) from e
            return FileResponse(
                prefix + ".TextGrid",
                background=cleanup,
                media_type="text/plain",
                filename="aligned.TextGrid",
            )

        elif output_format == FormatName.EAF:
            try:
                save_label_files(
                    words, parsed_xml, request.audio_duration, prefix, "eaf"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail="XML+SMIL file pair provided cannot be converted",
                ) from e
            return FileResponse(
                prefix + ".eaf",
                background=cleanup,
                media_type="text/xml",
                filename="aligned.eaf",
            )

        elif output_format == FormatName.SRT:
            try:
                save_subtitles(words, parsed_xml, prefix, "srt")
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail="XML+SMIL file pair provided cannot be converted",
                ) from e
            if tier == SubtitleTier.WORD:
                return FileResponse(
                    prefix + "_words.srt",
                    background=cleanup,
                    media_type="text/plain",
                    filename="aligned_words.srt",
                )
            else:
                return FileResponse(
                    prefix + "_sentences.srt",
                    background=cleanup,
                    media_type="text/plain",
                    filename="aligned_sentences.srt",
                )

        elif output_format == FormatName.VTT:
            try:
                save_subtitles(words, parsed_xml, prefix, "vtt")
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail="XML+SMIL file pair provided cannot be converted",
                ) from e
            if tier == SubtitleTier.WORD:
                return FileResponse(
                    prefix + "_words.vtt",
                    background=cleanup,
                    media_type="text/plain",
                    filename="aligned_words.vtt",
                )
            else:
                return FileResponse(
                    prefix + "_sentences.vtt",
                    background=cleanup,
                    media_type="text/plain",
                    filename="aligned_sentences.vtt",
                )

        else:
            raise HTTPException(
                status_code=500,
                detail="If this happens, FastAPI Enum validation didn't work so this is a bug!",
            )

    except Exception:
        # We don't normally use such a global exception, but in this case we really
        # need to make sure the temporary directory is cleaned up, so this except
        # catches any and all problems and wipes the temporary data
        temp_dir_object.cleanup()
        raise


# Mount the v1 version of the API to the root of the app
web_api_app.mount("/api/v1", v1)
