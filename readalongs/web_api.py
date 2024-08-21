"""REST-ish Web API for ReadAlongs Studio text manipulation operations using FastAPI.

See https://readalong-studio.herokuapp.com/api/v1/docs for the documentation.

You can spin up this Web API for development purposes on any platform with:
    pip install uvicorn
    cd readalongs/
    DEVELOPMENT=1 uvicorn readalongs.web_api:web_api_app --reload
- The --reload switch will watch for changes under the directory where it's
  running and reload the code whenever it changes, so it's best run in readalongs/
- DEVELOPMENT=1 tells the API to accept cross-origin requests (i.e. by sending the
  appropriate CORS headers) from development servers running on localhost, e.g.
  http://localhost:4200

For deployment, you can use the ORIGIN environment variable to set the URL of your
application in order to make it accept requests from that site.  For instance if
you deployed an application that uses it (such as Studio-Web) at
https://my.awesome.site you would set ORIGIN=https://my.awesome.site in your
environment variables.  This is usually done through an environment variable file
(or in a dashboard) and will depend on your hosting environment.

You can also spin up the API server grade (on Linux, not Windows) with gunicorn:
    pip install -r requirements.api.txt
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker readalongs.web_api:web_api_app

Once spun up, the documentation and API playground will be visible at
http://localhost:8000/api/v1/docs

"""

import os
import tempfile
from enum import Enum
from textwrap import dedent
from typing import Dict, List, Optional, Tuple, Union

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from lxml import etree
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from readalongs._version import READALONG_FILE_FORMAT_VERSION, VERSION
from readalongs.align import create_ras_from_text, save_label_files, save_subtitles
from readalongs.log import LOGGER, capture_logs
from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.convert_xml import convert_xml
from readalongs.text.make_dict import make_dict_list
from readalongs.text.tokenize_xml import tokenize_xml
from readalongs.text.util import parse_xml
from readalongs.util import get_langs

# Create the app
web_api_app = FastAPI()
middleware_args: Dict[str, Union[str, List[str]]]
if os.getenv("DEVELOPMENT", False):
    LOGGER.info(
        "Running in development mode, will allow requests from http://localhost:*"
    )
    # Allow requests from localhost dev servers
    middleware_args = dict(
        allow_origin_regex="http://localhost(:.*)?",
    )
else:
    # Allow requests *only* from mt app (or otherwise configured site name)
    middleware_args = dict(
        allow_origins=[
            os.getenv("ORIGIN", "https://readalong-studio.mothertongues.org"),
        ],
    )
web_api_app.add_middleware(
    CORSMiddleware, allow_methods=["GET", "POST", "OPTIONS"], **middleware_args
)

# Create the v1 version of the API
v1 = FastAPI()
# Call get_langs() when the server loads to load the languages into memory
LANGS = get_langs()
# Get the DTD
DTDPATH = os.path.join(os.path.dirname(__file__), "static", "read-along-1.2.dtd")
with open(DTDPATH) as dtdfh:
    DTD = etree.DTD(dtdfh)


class InputFormat(Enum):
    """The different formats supported for input to /assemble"""

    TEXT = "text/plain"
    RAS = "application/readalong+xml"


class AssembleRequest(BaseModel):
    """Base request for assemble"""

    input_text: Optional[str] = Field(None, alias="input")
    mime_type: Optional[InputFormat] = Field(None, alias="type")
    text_languages: List[str]
    debug: bool = False


class AssembleResponse(BaseModel):
    """Response from assemble with the ReadAlongs XML prepared and the rest."""

    lexicon: List[Tuple[str, str]]
    text_ids: str  # The text ID input for the decoder in plain text
    processed_ras: str  # The processed RAS XML is returned as a string
    input_request: Optional[AssembleRequest] = Field(None, alias="input")
    parsed: Optional[str] = None
    tokenized: Optional[str] = None
    g2ped: Optional[str] = None
    log: Optional[str] = None


class SupportedLanguage(BaseModel):
    code: str  # language code
    names: Dict[
        str, str
    ]  # Mapping from language to name of language in language (c'est-tu clair?)


@v1.get("/langs", response_model=List[SupportedLanguage])
async def langs() -> List[SupportedLanguage]:
    """Return the list of supported languages and their names as a dict.

    Returns:
        Supported languages as list with language codes and mapping of
        language code to name, including minimally the key "_" for the
        default display name (usually, but not always, in English).
        For example:

        [
            {"code": "alq", names: { "alq": "Anishinaabemowin", "_": "Algonquin" }},
            {"code": "atj", names: { "atj": "Nehiromowin", "_": "Atikamekw" }},
            {"code": "fra", names: { "fra": "Français", "_": "French" }},
            ...
        ]
    """
    langs, lang_names = LANGS
    return [
        SupportedLanguage(code=code, names=dict(_=lang_names[code])) for code in langs
    ]


@v1.post("/assemble", response_model=AssembleResponse)
async def assemble(
    request: AssembleRequest = Body(
        examples=[
            {
                "text": {
                    "summary": "A basic example with plain text input",
                    "value": {
                        "input": "hej verden",
                        "type": "text/plain",
                        "text_languages": ["dan", "und"],
                        "debug": False,
                    },
                },
                "xml": {
                    "summary": "A basic example with xml input",
                    "value": {
                        "input": "<?xml version='1.0' encoding='utf-8'?><read-along version=\"1.0\"><text><p><s>hej verden</s></p></text></read-along>",
                        "type": "application/readalong+xml",
                        "text_languages": ["dan", "und"],
                        "debug": False,
                    },
                },
            }
        ]
    ),
):
    """Create an input RAS from the given text (as plain text or XML).
    Also creates the required grammar, pronunciation dictionary,
    and text needed by the decoder.

    Encoding: all input and output is in UTF-8.

    Args (as dict items in the request body):
     - text_languages: the list of languages for g2p processing
     - debug: set to true for debugging (default: False)
     - type: type of input data, only `text/plain`
       or `application/readalong+xml` are currently supported
     - input: the input in the type specified

    Returns (as dict items in the response body):
     - lexicon: list of word IDs and their pronunciation
     - text_ids: the list of word_ids as a space-separated string
       for force-alignment
     - processed_xml: the XML with all the readalongs info in it
     - log: collected warnings and error messages
    """
    with capture_logs() as captured_logs:
        if request.mime_type == InputFormat.RAS:
            try:
                parsed = parse_xml(request.input_text or "")
            except etree.ParseError as e:
                raise HTTPException(
                    status_code=422, detail="XML provided is not well-formed"
                ) from e
            if not DTD.validate(parsed):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "ReadAlong provided is not valid: %s"
                        % DTD.error_log.filter_from_errors()[0]
                    ),
                )
        elif request.mime_type == InputFormat.TEXT:
            parsed = parse_xml(
                create_ras_from_text(
                    (request.input_text or "").splitlines(keepends=True),
                    text_languages=request.text_languages,
                )
            )

        else:  # pragma: no cover
            raise HTTPException(
                status_code=500,
                detail="If this happens, FastAPI Enum validation didn't work so this is a bug!",
            )

        # tokenize
        tokenized = tokenize_xml(parsed)

        if not tokenized.xpath(".//w"):
            raise HTTPException(
                status_code=422,
                detail="Could not find any words to align in the text.",
            )

        # add ids
        ids_added = add_ids(tokenized)

        # g2p
        g2ped, valid = convert_xml(ids_added)
        if not valid:
            raise HTTPException(
                status_code=422,
                detail="g2p could not be performed, please check your text or your language code. Logs: "
                + captured_logs.getvalue(),
            )
        # create grammar
        dict_data, text_input = create_grammar(g2ped)

    response = AssembleResponse(
        lexicon=dict_data,
        text_ids=text_input,
        processed_ras=etree.tostring(g2ped, encoding="utf8").decode(),
        log=captured_logs.getvalue(),
    )

    if request.debug:
        response.input_request = request
        response.parsed = etree.tostring(parsed, encoding="utf8")
        response.tokenized = etree.tostring(tokenized, encoding="utf8")
        response.g2ped = etree.tostring(g2ped, encoding="utf8")
    return response


def create_grammar(xml):
    """Create the grammar and dictionary data from w elements in the given XML"""

    word_elements = xml.xpath("//w")
    dict_data = make_dict_list(word_elements)
    text_data = " ".join(xml.xpath("//w/@id"))
    return dict_data, text_data


class WordAlignment(BaseModel):
    """Word alignment extracted from RAS"""

    word_id: Optional[str] = Field(None, alias="id")
    start: float
    end: float


class Alignment(BaseModel):
    """Alignment extracted from RAS"""

    words: List[WordAlignment]


def get_alignment(xml: etree.ElementTree) -> List[dict]:
    """Get the word alignments from the given XML"""

    word_elements = xml.xpath("//w")
    alignment = []
    for e in word_elements:
        if "time" not in e.attrib or "dur" not in e.attrib:
            continue
        # round to millisecondes as elsewhere to avoid imprecisions
        alignment.append(
            {
                "id": e.attrib["id"],
                "start": round(float(e.attrib["time"]), 3),
                "end": round(float(e.attrib["time"]) + float(e.attrib["dur"]), 3),
            }
        )
    return alignment


class OutputFormat(Enum):
    """The different formats supported to represent readalong alignments"""

    TEXTGRID = "textgrid"  # Praat TextGrid format
    EAF = "eaf"  # ELAN EAF format
    SRT = "srt"  # SRT subtitle format
    VTT = "vtt"  # VTT subtitle format


class ConvertRequest(BaseModel):
    """Convert Request contains the RAS-processed XML"""

    dur: Union[float, None] = Field(
        examples=[2.01],
        gt=0.0,
        title="The duration of the audio used to create the alignment, in seconds.",
        default=None,
    )

    ras: str = Field(
        title="The time-aligned XML output produced by `readalongs align`.",
        examples=[
            dedent(
                """\
                <?xml version='1.0' encoding='utf-8'?>
                <read-along version="%s">
    <meta name="generator" content="@readalongs/studio (cli) %s"/>
                    <text xml:lang="dan" fallback-langs="und" id="t0">
                        <body id="t0b0">
                            <div type="page" id="t0b0d0">
                                <p id="t0b0d0p0">
                                    <s id="t0b0d0p0s0">
                                        <w id="t0b0d0p0s0w0" ARPABET="HH EH Y" time="0.14" dur="0.64">hej</w>
                                        <w id="t0b0d0p0s0w1" ARPABET="V Y D EH N" time="0.78" dur="1.11">verden</w>
                                    </s>
                                </p>
                            </div>
                        </body>
                    </text>
                </read-along>"""
                % (READALONG_FILE_FORMAT_VERSION, VERSION)
            )
        ],
    )


class SubtitleTier(Enum):
    """Which tier of the alignment information is returned"""

    SENTENCE = "sentence"
    WORD = "word"


@v1.post("/convert_alignment/{output_format}")  # noqa: C901
async def convert_alignment(  # noqa: C901
    request: ConvertRequest,
    output_format: OutputFormat,
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
     - dur: duration in seconds of the audio file used to create the alignment,
       will be inferred from the alignments if not present
     - ras: the ReadAlongs file produced by `readalongs align`

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
        parsed_xml = parse_xml(request.ras)
    except etree.XMLSyntaxError as e:
        raise HTTPException(
            status_code=422, detail="ReadAlong provided is not well formed"
        ) from e
    if not DTD.validate(parsed_xml):
        raise HTTPException(
            status_code=422,
            detail=(
                "ReadAlong provided is not valid: %s"
                % DTD.error_log.filter_from_errors()[0]
            ),
        )

    words = get_alignment(parsed_xml)
    if request.dur is None:
        request.dur = words[-1]["end"]

    # Data privacy consideration: we have to make sure this temporary directory gets
    # deleted after the call returns, as we promise in the API documentation.
    temp_dir_object = tempfile.TemporaryDirectory()
    temp_dir_name = temp_dir_object.name
    cleanup = BackgroundTask(temp_dir_object.cleanup)
    prefix = os.path.join(temp_dir_name, "aligned")
    LOGGER.info("Temporary directory: %s", temp_dir_name)

    try:
        if output_format == OutputFormat.TEXTGRID:
            try:
                save_label_files(words, parsed_xml, request.dur, prefix, "textgrid")
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail="ReadAlong provided cannot be converted",
                ) from e
            return FileResponse(
                prefix + ".TextGrid",
                background=cleanup,
                media_type="text/plain",
                filename="aligned.TextGrid",
            )

        elif output_format == OutputFormat.EAF:
            try:
                save_label_files(words, parsed_xml, request.dur, prefix, "eaf")
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail="ReadAlong provided cannot be converted",
                ) from e
            return FileResponse(
                prefix + ".eaf",
                background=cleanup,
                media_type="text/xml",
                filename="aligned.eaf",
            )

        elif output_format == OutputFormat.SRT:
            try:
                save_subtitles(words, parsed_xml, prefix, "srt")
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail="ReadAlong provided cannot be converted",
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

        elif output_format == OutputFormat.VTT:
            try:
                save_subtitles(words, parsed_xml, prefix, "vtt")
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail="ReadAlong provided cannot be converted",
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

        else:  # pragma: no cover
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
