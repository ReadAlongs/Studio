###########################################
#
# util.py
#
# Just some shared functions
#
# TODO: Add Google standard format docstrings
############################################

import json
import os
import re
import zipfile
from collections import OrderedDict
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path
from typing import IO, Union
from unicodedata import normalize

from lxml import etree

from readalongs._version import VERSION

# removed "try: unicode() except" block (was for Python 2), but this file uses unicode()
# too many times, so define it anyway.
unicode = str
# todo: sync with web component major and minor releases
CURRENT_WEB_APP_VERSION = "1.4.x"


def ensure_dirs(path):
    dirname = os.path.dirname(path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)


def xpath_default(xml, query, default_namespace_prefix="i"):
    nsmap = xml.nsmap if hasattr(xml, "nsmap") else xml.getroot().nsmap
    nsmap = dict(
        ((x, y) if x else (default_namespace_prefix, y)) for (x, y) in nsmap.items()
    )
    for e in xml.xpath(query, namespaces=nsmap):
        yield e


def get_attrib_recursive(element, *attribs):
    """Find the first attribute in attribs in element or its closest ancestor
    that has any of the attributes in attribs.

    Usage examples:
        get_attrib_recursive(el, "fallback-langs")
        get_attrib_recursive(el, "xml:lang", "lang")

    Args:
        element: an etree element where to search for attributes in attribs
        attribs: one or more attribute label(s) to search for

    Returns:
        the value of the first attribute in attribes found in element or the
        closest ancestor that has any of the attributes in attribs, or None
    """
    for attrib in attribs:
        # We could also element.attrib[attrib] instead of xpath, but it only
        # works for attributes without a name, like attrib="lang", while xpath
        # also works for attributes with a namespace, like attrib="xml:lang".
        path = element.xpath("./@" + attrib)
        if path:
            return path[0]
    if element.getparent() is not None:
        return get_attrib_recursive(element.getparent(), *attribs)
    else:
        return None


def iterate_over_text(element: etree.ElementTree):
    """Iterate over all actual text contained with element and its sub-elements

    Yields:
        (language_code, text) pairs
    """
    lang = get_lang_attrib(element)
    if element.text:
        yield (lang, element.text)
    for child in element:
        yield from iterate_over_text(child)
        if child.tail:
            yield (lang, child.tail)


def get_word_text(word_element: etree.ElementTree) -> str:
    """Given a word element, extract all its text"""
    return "".join(text for _, text in iterate_over_text(word_element))


def get_lang_attrib(element: etree.ElementTree):
    """Return the xml:lang (in priority) or lang (fallback) attribute from element
    or its closest ancestor that has either, or None when neither is found.
    """
    return get_attrib_recursive(element, "xml:lang", "lang")


def is_do_not_align(element):
    dna = element.attrib.get("do-not-align", "")
    return dna in ("true", "True", "TRUE", "1")


def load_xml(input_path: Union[str, Path, IO]) -> etree.ElementTree:
    """Safely load an XML file with etree.parse to respect encoding

    Return: the root of the XML etree

    Args:
        input_path: filename or open input IO handle

    Raises:
        etree.ParseError: if there is a problem parsing the XML contents
        OSError: if there is a problem opening the file
    """
    # resolve_entities=False is a safety issue, prevents XML bombs.
    return etree.parse(
        input_path,
        parser=etree.XMLParser(resolve_entities=False),
    ).getroot()


def parse_xml(xml_text: Union[str, bytes]) -> etree.ElementTree:
    """Safely parse an XML as input text

    Return: the root of the XML etree

    Args:
        xml_text: the XML text contents to parse

    Raises:
        etree.ParseError: if there is a problem parsing the XML contents
    """
    return etree.fromstring(
        xml_text if isinstance(xml_text, bytes) else bytes(xml_text, encoding="utf8"),
        # resolve_entities=False is a safety issue, prevents XML bombs.
        parser=etree.XMLParser(resolve_entities=False),
    )


def load_xml_zip(zip_path, input_path) -> etree.ElementTree:
    with zipfile.ZipFile(zip_path, "r") as fin_zip:
        with fin_zip.open(input_path, "r") as fin:
            return load_xml(fin)


def write_xml(output_filelike, xml):
    """Write XML to already opened file-like object"""
    output_filelike.write(etree.tostring(xml, encoding="utf-8", xml_declaration=True))
    output_filelike.write("\n".encode("utf-8"))


def save_xml(output_path, xml):
    """Save XML to specific PATH"""
    ensure_dirs(output_path)
    with open(output_path, "wb") as fout:
        write_xml(fout, xml)


def save_xml_zip(zip_path, output_path, xml):
    ensure_dirs(zip_path)
    with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as fout_zip:
        fout_zip.writestr(
            output_path,
            etree.tostring(xml, encoding="utf-8", xml_declaration=True) + "\n",
        )


def load_txt(input_path):
    with open(input_path, "r", encoding="utf-8-sig") as fin:
        return fin.read()


def load_txt_zip(zip_path, input_path):
    with zipfile.ZipFile(zip_path, "r") as fin_zip:
        with fin_zip.open(input_path, "r") as fin:
            fin_utf8 = TextIOWrapper(fin, encoding="utf-8")
            return fin_utf8.read()


def save_txt(output_path, txt):
    ensure_dirs(output_path)
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(txt)


def save_txt_zip(zip_path, output_path, txt):
    ensure_dirs(zip_path)
    with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as fout_zip:
        fout_zip.writestr(output_path, txt.encode("utf-8"))


def load_json(input_path):
    with open(input_path, "r", encoding="utf-8-sig") as fin:
        return json.load(fin, object_pairs_hook=OrderedDict)


def load_json_zip(zip_path, input_path):
    with zipfile.ZipFile(zip_path, "r") as fin_zip:
        with fin_zip.open(input_path, "r") as fin:
            fin_utf8 = TextIOWrapper(fin, encoding="utf-8")
            return json.loads(fin_utf8.read(), object_pairs_hook=OrderedDict)


def save_json(output_path, obj):
    ensure_dirs(output_path)
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(unicode(json.dumps(obj, ensure_ascii=False, indent=4)))


def save_json_zip(zip_path, output_path, obj):
    ensure_dirs(zip_path)
    txt = unicode(json.dumps(obj, ensure_ascii=False, indent=4))
    with zipfile.ZipFile(zip_path, "a") as fout_zip:
        fout_zip.writestr(output_path, txt.encode("utf-8"))


def copy_file_to_zip(zip_path, origin_path, destination_path):
    ensure_dirs(zip_path)
    with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as fout_zip:
        fout_zip.write(origin_path, destination_path)


MINIMAL_INDEX_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="application-name" content="read along">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=5.0">
        <meta name="generator" content="@readalongs/studio (cli) {studio_version}">
        <title>{title}</title>
        <!-- Import fonts. Material Icons are needed by the web component -->
        <link href="https://fonts.googleapis.com/css?family=Lato%7CMaterial+Icons%7CMaterial+Icons+Outlined" rel="stylesheet">
    </head>

    <body>
        <!-- Here is how you declare the Web Component. Supported languages: eng, fra, spa -->
        <read-along href="{text}" audio="{audio}" theme="{theme}" language="eng">
            <span slot='read-along-header'>{header}</span>
            <span slot='read-along-subheader'>{subheader}</span>
        </read-along>
    </body>

    <!-- The last step needed is to import the package -->
    <script type="module" src='https://unpkg.com/@readalongs/web-component@{version}/dist/web-component/web-component.esm.js'></script>
</html>
"""


def save_minimal_index_html(
    output_path,
    tokenized_xml_basename,
    audio_basename,
    title,
    header,
    subheader,
    theme,
):
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(
            MINIMAL_INDEX_HTML_TEMPLATE.format(
                title=title,
                text=tokenized_xml_basename,
                audio=audio_basename,
                theme=theme,
                header=header,
                subheader=subheader,
                version=CURRENT_WEB_APP_VERSION,
                studio_version=VERSION,
            )
        )


def unicode_normalize_xml(element):
    if element.text:
        element.text = normalize("NFD", unicode(element.text))
    for child in element.getchildren():
        unicode_normalize_xml(child)
        if child.tail:
            child.tail = normalize("NFD", unicode(child.tail))


def parse_time(time_string: str) -> int:
    """Parse a time stamp in h/m/s(default)/ms or any combination of these units.

    Args:
        time_string (str): timestamp, e.g., "0.23s", "5.234" (implied s), "1234 ms",
            "1h 10m 12.345s", "00h00m00.000". Supported units: h, m, s (default), ms
            and any combination thereof.

    Returns:
        int: time represented by time_string in milliseconds

    Raises:
        ValueError: if time_string cannot be parsed
    """
    try:
        if not time_string.strip():
            raise ValueError("empty time string")
        prev_end = 0
        time_in_ms = 0
        for unit_match in re.finditer(r"ms|h|m|s", time_string):
            # float() raises ValueError if text before the unit is not a valid number
            numerical_part = float(time_string[prev_end : unit_match.start()])
            unit_part = unit_match.group()
            if unit_part == "h":
                time_in_ms += int(numerical_part * 3600000)
            elif unit_part == "m":
                time_in_ms += int(numerical_part * 60000)
            elif unit_part == "s":
                time_in_ms += int(numerical_part * 1000)
            else:  # unit_part == "ms":
                time_in_ms += int(numerical_part)
            prev_end = unit_match.end()
        last_part = time_string[prev_end:].strip()
        if last_part:
            time_in_ms += int(float(last_part) * 1000)
        return time_in_ms
    except ValueError as e:
        # e might have been raised by any of the float() constructor
        raise ValueError(
            f'cannot parse "{time_string}" as a valid time in h/m/s/ms'
        ) from e


# todo: synchronize with web-component readme
# https://github.com/ReadAlongs/Web-Component/blob/main/packages/studio-web/src/app/demo/demo.component.ts#L49
# https://github.com/ReadAlongs/Web-Component/blob/main/packages/studio-web/src/app/demo/demo.component.ts#L328
TEMPLATE_README_TXT = """\
Web Deployment Guide
====================

This folder has everything you need to host your ReadAlong on your own server.

Your audio ({audio}), (optional) image(s) asset(s), and alignment ({text}) are stored in this folder.

Your index.html file demonstrates the snippet and imports needed to host the ReadAlong on your server.

Please host all assets on your server, include the font and package imports defined in the index.html in your website's imports, and include the corresponding <read-along> snippet everywhere you would like your ReadAlong to be displayed.



WordPress Deployment Guide
==========================

Setup the plugin (do this once)
-------------------------------

Install and activate our plugin 'read-along-web-app-loader' on your WordPress site.

See https://github.com/ReadAlongs/Studio-Web/tree/main/packages/web-component/wordpress-plugin for more information


Deploy the read-along
---------------------

Upload the images and {text} and {audio} to your Media Library of your WordPress site.

Use the text editor to paste the snippet below in your WordPress page:

        ---- WP Deployment SNIPPET ----
<!-- wp:html -->
[read_along_web_app_loader version="{version}"]
    <read-along href="{wp_upload_folder}{text}" audio="{wp_upload_folder}{audio}" image-assets-folder="{wp_upload_folder}" theme="{theme}" language="eng">
        <span slot='read-along-header'>{header}</span>
        <span slot='read-along-subheader'>{subheader}</span>
    </read-along>
[/read_along_web_app_loader]
<!-- /wp:html -->
        ----- END OF SNIPPET----
"""


def save_readme_txt(
    output_path,
    tokenized_xml_basename,
    audio_basename,
    header,
    subheader,
    theme,
):
    # setup path for default WordPress upload directory
    today = datetime.now()
    wp_upload_folder = "/wp-content/uploads/{:%Y/%m}/".format(today)
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(
            TEMPLATE_README_TXT.format(
                version=CURRENT_WEB_APP_VERSION,
                text=tokenized_xml_basename,
                audio=audio_basename,
                theme=theme,
                header=header,
                subheader=subheader,
                wp_upload_folder=wp_upload_folder,
            )
        )
