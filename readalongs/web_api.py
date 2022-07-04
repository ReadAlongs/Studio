import io
import os
from typing import List, Union

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from lxml import etree
from pydantic import BaseModel

from readalongs.align import create_tei_from_text, get_sequences
from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.convert_xml import convert_xml
from readalongs.text.make_dict import make_dict_object
from readalongs.text.make_fsg import make_fsg
from readalongs.text.make_jsgf import make_jsgf
from readalongs.text.tokenize_xml import tokenize_xml

web_api_app = FastAPI()
v1 = FastAPI()

if not os.getenv("PRODUCTION", False):
    origins = ["http://localhost:4200"]  # Allow requests from Angular app
    web_api_app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class RequestBase(BaseModel):
    text_languages: List[str]
    encoding: str = "utf-8"
    debug: bool = False


class PlainTextRequest(RequestBase):
    text: str


class XMLRequest(RequestBase):
    xml: str


def process_xml(func):
    # Wrapper for processing XML
    def wrapper(xml, **kwargs):
        parsed = etree.fromstring(bytes(xml.xml, encoding=xml.encoding))
        processed = func(parsed, **kwargs)
        return etree.tostring(processed, encoding="utf-8", xml_declaration=True)

    return wrapper


@v1.post("/prepare")
async def readalong(input: Union[XMLRequest, PlainTextRequest]):
    # take XML as default
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
        "dict": dict_data,
        "jsgf": jsgf,
        "text_ids": text_input,
        "processed_xml": etree.tostring(g2ped, encoding="utf8").decode(),
    }
    if input.debug:
        response["input"] = (input,)
        response["parsed"] = (parsed,)
        response["tokenized"] = (tokenized,)
        response["g2ped"] = g2ped
    return response


def create_grammar(xml):
    dict_data = make_dict_object(xml.xpath("//w"))
    fsg_data = make_jsgf(xml.xpath("//w"), filename="test")
    text_data = " ".join(xml.xpath("//w/@id"))
    return dict_data, fsg_data, text_data


web_api_app.mount("/api/v1", v1)
