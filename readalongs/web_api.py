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
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Dict, List, Optional, Union

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from lxml import etree
from pydantic import BaseModel, Field

from readalongs.align import create_tei_from_text, save_label_files
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
    encoding: str = "utf-8"
    debug: bool = False


class PlainTextRequest(RequestBase):
    """Request to assemble with input as plain text"""

    text: str


class XMLRequest(RequestBase):
    """Request to assemble with input as XML"""

    xml: str


class AssembleResponse(BaseModel):
    lexicon: Dict[str, str]  # A dictionary of the form {lang_id: lang_name }
    jsgf: str  # The JSGF-formatted grammar in plain text
    text_ids: str  # The text ID input for the decoder in plain text
    processed_xml: str  # The processed XML is returned as a string
    input: Optional[Union[XMLRequest, PlainTextRequest]]
    parsed: Optional[str]
    tokenized: Optional[str]
    g2ped: Optional[str]


def process_xml(func):
    # Wrapper for processing XML, reads the XML with proper encoding,
    # then applies the given function to it,
    # then converts the result back to utf-8 XML and returns it
    def wrapper(xml, **kwargs):
        parsed = etree.fromstring(bytes(xml.xml, encoding=xml.encoding))
        processed = func(parsed, **kwargs)
        return etree.tostring(processed, encoding="utf-8", xml_declaration=True)

    return wrapper


@v1.get("/langs", response_model=Dict[str, str])
async def langs() -> Dict[str, str]:
    """Return the list of supported languages and their names as a dict."""

    return LANGS[1]


@v1.post("/assemble", response_model=AssembleResponse)
async def assemble(
    input: Union[XMLRequest, PlainTextRequest] = Body(
        examples={
            "text": {
                "summary": "A basic example with plain text input",
                "value": {
                    "text": "hej verden",
                    "text_languages": ["dan", "und"],
                    "encoding": "utf-8",
                    "debug": False,
                },
            },
            "xml": {
                "summary": "A basic example with xml input",
                "value": {
                    "xml": "<?xml version='1.0' encoding='utf-8'?><TEI><text><p><s>hej verden</s></p></text></TEI>",
                    "text_languages": ["dan", "und"],
                    "encoding": "utf-8",
                    "debug": False,
                },
            },
        }
    )
):
    """Create an input TEI from the given text (as plain text or XML).
    Also creates the required grammar, pronunciation dictionary,
    and text needed by the decoder.

    Args (as dict items in the request body):
     - text_languages: the list of languages for g2p processing
     - encoding: encoding (default: "utf-8")
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

    if isinstance(input, XMLRequest):
        try:
            parsed = etree.fromstring(bytes(input.xml, encoding=input.encoding))
        except etree.XMLSyntaxError as e:
            raise HTTPException(
                status_code=422, detail="XML provided is not valid"
            ) from e
    elif isinstance(input, PlainTextRequest):
        parsed = io.StringIO(input.text).readlines()
        parsed = etree.fromstring(
            bytes(
                create_tei_from_text(parsed, text_languages=input.text_languages),
                encoding="utf-8",
            )
        )
    # tokenize
    tokenized = tokenize_xml(parsed)
    # add ids
    ids_added = add_ids(tokenized)
    # g2p
    g2ped, valid = convert_xml(ids_added)
    if not valid:
        raise HTTPException(
            status_code=422, detail="g2p could not be performed"
        )  # TODO: do we want to return a 400 here? better error message
    # create grammar
    dict_data, jsgf, text_input = create_grammar(g2ped)
    response = {
        "lexicon": dict_data,
        "jsgf": jsgf,
        "text_ids": text_input,
        "processed_xml": etree.tostring(g2ped, encoding="utf8").decode(),
    }

    if input.debug:
        response["input"] = input.dict()
        response["parsed"] = etree.tostring(parsed, encoding="utf8")
        response["tokenized"] = etree.tostring(tokenized, encoding="utf8")
        response["g2ped"] = etree.tostring(g2ped, encoding="utf8")
    return response


def create_grammar(xml):
    # Create the grammar and dictionary data from w elements in the given XML
    word_elements = xml.xpath("//w")
    dict_data = make_dict_object(word_elements)
    fsg_data = make_jsgf(word_elements, filename="test")
    text_data = " ".join(xml.xpath("//w/@id"))
    return dict_data, fsg_data, text_data


class ConvertRequest(BaseModel):
    """Convert Request contains the RAS-processed XML and SMIL alignments"""

    audio_length: float = Field(
        example=2.01,
        gt=0.0,
        title="The length of the audio used to create the alignment, in seconds.",
    )

    encoding: str = Field(
        example="utf-8",
        title="Only utf-8 is supported now, but contact us if you might need support for a different enciding.",
    )

    output_format: str = Field(
        example="TextGrid",
        regex="^(?i)(eaf|TextGrid)$",
        title="Format to convert to, one of TextGrid (Praat), eaf (ELAN).",
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


class ConvertResponse(BaseModel):
    """Convert response has the requesed converted file's contents"""

    file_contents: str = Field(
        title="Full contents of the converted file in the format requested."
    )


@v1.post("/convert_alignment", response_model=ConvertResponse)
async def convert_alignment(input: ConvertRequest) -> ConvertResponse:
    """Convert an alignment to a different format.

    Args (as dict items in the request body):
     - audio_length: duration in seconds of the audio file used to create the alignment
     - encoding: use utf-8, other encodings are not supported (yet)
     - output_format: one of TextGrid (Praat), eaf (ELAN), ...
     - xml: the XML file produced by /assemble
     - smil: the SMIL file produced by SoundSwallower(.js)

    Data privacy consideration: due to limitations of the libraries used to perform
    some of these conversions, the output file may be temporarily stored on disk,
    but it gets deleted immediately, before it is even returned by this endpoint.

    Returns:
     - file_contents: the contents of the file converted in the requested format
    """
    try:
        parsed_xml = etree.fromstring(bytes(input.xml, encoding=input.encoding))
    except etree.XMLSyntaxError as e:
        raise HTTPException(status_code=422, detail="XML provided is not valid") from e

    if input.encoding not in ["utf-8", "utf8", "UTF-8", "UTF8", ""]:
        raise HTTPException(
            status_code=422,
            detail="Please use utf-8 as your encoding, or contact us with a description of how and why you would like to use a different encoding",
        )

    try:
        words = parse_smil(input.smil)
    except ValueError as e:
        raise HTTPException(status_code=422, detail="SMIL provided is not valid") from e

    output_format = input.output_format.lower()
    if output_format == "textgrid":
        with TemporaryDirectory() as temp_dir_name:
            prefix = os.path.join(temp_dir_name, "f")
            save_label_files(words, parsed_xml, input.audio_length, prefix, "textgrid")
            with open(prefix + ".TextGrid", mode="r", encoding="utf-8") as f:
                textgrid_text = f.read()

        return ConvertResponse(file_contents=textgrid_text)

    elif output_format == "eaf":
        with TemporaryDirectory() as temp_dir_name:
            prefix = os.path.join(temp_dir_name, "f")
            save_label_files(words, parsed_xml, input.audio_length, prefix, "eaf")
            with open(prefix + ".eaf", mode="r", encoding="utf-8") as f:
                eaf_text = f.read()

        return ConvertResponse(file_contents=eaf_text)

    else:
        raise HTTPException(
            status_code=500,
            detail="Invalid output_format should have been caught by fastAPI already...",
        )


# Mount the v1 version of the API to the root of the app
web_api_app.mount("/api/v1", v1)
