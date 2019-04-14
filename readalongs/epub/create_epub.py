#!/usr/bin/env python3
# -*- coding: utf-8 -*-

######################################################################
#
# create_epub.py
#
######################################################################

from __future__ import print_function, unicode_literals, division
from io import open
import argparse
import zipfile
import pystache
import logging
from collections import defaultdict
from g2p.util import *

OEBPS_PATH = "OEBPS"
MIMETYPE_ORIGIN_PATH = "epub/templates/mimetype"
MIMETYPE_DEST_PATH = "mimetype"
CONTAINER_ORIGIN_PATH = "epub/templates/container.xml"
CONTAINER_DEST_PATH = "META-INF/container.xml"
PACKAGE_ORIGIN_PATH = "epub/templates/package.opf"
PACKAGE_DEST_PATH = os.path.join(OEBPS_PATH, "package.opf")


def xpath_default(xml, query, default_namespace_prefix="i"):
    nsmap = xml.nsmap if hasattr(xml, "nsmap") else xml.getroot().nsmap
    nsmap = dict(((x,y) if x else (default_namespace_prefix,y))
                        for (x,y) in nsmap.items())
    for e in xml.xpath(query, namespaces=nsmap):
        yield e

def process_src_attrib(src_text, id_prefix, mimetypes):
    filename = src_text.split("#")[0]
    filename_without_ext, ext = os.path.splitext(filename)
    ext = ext.strip(".")
    if ext not in mimetypes:
        logging.warning("Unknown extension in SMIL: %s", ext)
        return None
    entry = {
        "origin_path": filename,
        "dest_path": filename,
        "ext": ext,
        "id": id_prefix + os.path.basename(filename_without_ext),
        "mimetype": mimetypes[ext]
    }
    return entry


def extract_files_from_SMIL(input_path):
    smil = load_xml(input_path)
    found_files = defaultdict(list)
    dirname = os.path.dirname(input_path)

    found_files["smil"].append({
        "origin_path": input_path,
        "dest_path": os.path.basename(input_path),
        "id": "main",
        "mimetype": "application/smil+xml"
    })

    queries = [
        { "xpath": ".//i:text/@src",
          "id_prefix": "",
          "mimetypes": {
            "xhtml": "application/xhtml+xml"
        }},
        { "xpath": ".//i:audio/@src",
          "id_prefix": "audio-",
          "mimetypes": {
            "wav": "audio/wav",
            "mp3": "audio/mpeg"
        }}
    ]

    for query in queries:
        for src_text in xpath_default(smil, query["xpath"]):
            entry = process_src_attrib(src_text, query["id_prefix"], query["mimetypes"])
            if entry is not None and entry not in found_files[entry["ext"]]:
                found_files[entry["ext"]].append(entry)

    within_xhtml_queries = [
        { "xpath": ".//i:img/@src",
          "id_prefix": "img-",
          "mimetypes": {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif"
        }}
    ]
    for entry in found_files["xhtml"]:
        origin_path = os.path.join(dirname, entry["origin_path"])
        xhtml = load_xml_with_encoding(origin_path)
        for query in within_xhtml_queries:
            for src_text in xpath_default(xhtml, query["xpath"] ):
                entry = process_src_attrib(src_text, query["id_prefix"], query["mimetypes"])
                if entry is not None and entry not in found_files[entry["ext"]]:
                    found_files[entry["ext"]].append(entry)
    return found_files


def main(input_path, output_path):
    if os.path.exists(output_path):
        os.remove(output_path)
    ensure_dirs(output_path)
    input_dirname = os.path.dirname(input_path)

    # mimetype file
    copy_file_to_zip(output_path, MIMETYPE_ORIGIN_PATH, MIMETYPE_DEST_PATH)

    # container.xml file
    container_template = load_txt(CONTAINER_ORIGIN_PATH)
    container_txt = pystache.render(container_template, {"package_path":PACKAGE_DEST_PATH})
    save_txt_zip(output_path, CONTAINER_DEST_PATH, container_txt)

    # the SMIL and all the files referenced in the SMIL
    found_files = extract_files_from_SMIL(input_path)
    package_template = load_txt(PACKAGE_ORIGIN_PATH)
    package_txt = pystache.render(package_template, found_files)
    save_txt_zip(output_path, PACKAGE_DEST_PATH, package_txt)

    for ext, entries in found_files.items():
        for entry in entries:
            origin_path = os.path.join(input_dirname, entry["origin_path"])
            if not os.path.exists(origin_path):
                logging.warning("Cannot find file %s to copy into EPUB file", origin_path)
                continue
            dest_path = os.path.join(OEBPS_PATH, entry["dest_path"])
            copy_file_to_zip(output_path, origin_path, dest_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert SMIL document to an EPUB with a Media Overlay')
    parser.add_argument('input', type=str, help='Input SMIL')
    parser.add_argument('output', type=str, help='Output EPUB')
    args = parser.parse_args()
    main(args.input, args.output)
