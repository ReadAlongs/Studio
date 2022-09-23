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
from typing import Dict, List, Optional, Union

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from lxml import etree
from pydantic import BaseModel, Field

from readalongs.align import create_tei_from_text
from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.convert_xml import convert_xml
from readalongs.text.make_dict import make_dict_object
from readalongs.text.make_fsg import make_jsgf
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


class LangsResponse(BaseModel):
    """List of languages supported by Studio, a dictionary of the form {land_id: lang_name}"""

    langs: Dict[str, str] = Field(
        example={
            "lc1": "Language Name 1",
            "lc2": "Language Name 2",
            "lc3": "Language Name 3",
        }
    )


@v1.get("/langs", response_model=LangsResponse)
async def langs() -> LangsResponse:
    """Return the list of supported languages and their names as a dict."""

    return LangsResponse(langs=LANGS[1])


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
            status_code=400, detail="g2p could not be performed"
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


# Mount the v1 version of the API to the root of the app
web_api_app.mount("/api/v1", v1)
