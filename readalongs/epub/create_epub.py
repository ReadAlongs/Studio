#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# create_epub.py
#
######################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import shutil

import chevron

from readalongs.log import LOGGER
from readalongs.text.util import (
    copy_file_to_zip,
    ensure_dirs,
    load_txt,
    load_xml,
    save_txt,
    save_txt_zip,
    xpath_default,
)

EPUB_PATH = "EPUB"
RESOURCES = os.path.dirname(__file__)
MIMETYPE_ORIGIN_PATH = os.path.join(RESOURCES, "templates/mimetype")
MIMETYPE_DEST_PATH = "mimetype"
CONTAINER_ORIGIN_PATH = os.path.join(RESOURCES, "templates/container.xml")
CONTAINER_DEST_PATH = "META-INF/container.xml"
PACKAGE_ORIGIN_PATH = os.path.join(RESOURCES, "templates/package.opf")
PACKAGE_DEST_PATH = os.path.join(EPUB_PATH, "package.opf")
STYLESHEET_ORIGIN_PATH = os.path.join(RESOURCES, "templates/stylesheet.css")
STYLESHEET_DEST_PATH = os.path.join(EPUB_PATH, "stylesheet.css")


def process_src_attrib(src_text, id_prefix, mimetypes):
    filename = src_text.split("#")[0]
    filename_without_ext, ext = os.path.splitext(filename)
    ext = ext.strip(".")
    if ext not in mimetypes:
        LOGGER.warning("Unknown extension in SMIL: %s", ext)
        return None
    entry = {
        "origin_path": filename,
        "dest_path": filename,
        "ext": ext.lower(),
        "id": id_prefix + os.path.basename(filename_without_ext),
        "mimetype": mimetypes[ext],
    }
    return entry


def extract_files_from_SMIL(input_path):
    smil = load_xml(input_path)
    found_files = {}
    xhtml_ids = []
    dirname = os.path.dirname(input_path)

    # add media referenced in the SMIL file itself
    queries = [
        {
            "xpath": ".//i:text/@src",
            "id_prefix": "",
            "mimetypes": {"xhtml": "application/xhtml+xml"},
        },
        {
            "xpath": ".//i:audio/@src",
            "id_prefix": "audio-",
            "mimetypes": {"wav": "audio/wav", "mp3": "audio/mpeg"},
        },
    ]

    for query in queries:
        for src_text in xpath_default(smil, query["xpath"]):
            entry = process_src_attrib(src_text, query["id_prefix"], query["mimetypes"])
            if entry is not None and entry["origin_path"] not in found_files:
                if entry["mimetype"] == "application/xhtml+xml":
                    entry["overlay"] = 'media-overlay="overlay"'
                    xhtml_ids.append({"id": entry["id"]})
                found_files[entry["origin_path"]] = entry

    # add media referenced within the xhtml files (e.g. imgs)
    within_xhtml_queries = [
        {
            "xpath": ".//i:img/@src",
            "id_prefix": "img-",
            "mimetypes": {
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "gif": "image/gif",
            },
        }
    ]

    SEARCHABLE_EXTENSIONS = ["xhtml"]
    for entry in found_files.values():
        if entry["ext"] not in SEARCHABLE_EXTENSIONS:
            continue
        origin_path = os.path.join(dirname, entry["origin_path"])
        xhtml = load_xml(origin_path)
        for query in within_xhtml_queries:
            for src_text in xpath_default(xhtml, query["xpath"]):
                entry = process_src_attrib(
                    src_text, query["id_prefix"], query["mimetypes"]
                )
                if entry is not None and entry["origin_path"] not in found_files:
                    found_files[entry["origin_path"]] = entry

    # add this file
    found_files[input_path] = {
        "origin_path": input_path,
        "dest_path": os.path.basename(input_path),
        "id": "overlay",
        "mimetype": "application/smil+xml",
        "ext": "smil",
    }

    return {"media": found_files.values(), "xhtml": xhtml_ids}


def copy_file_to_dir(output_path, origin_path, dest_path):
    """Copy file to a directory, mimicking the interface of
    copy_file_to_zip."""
    shutil.copy(origin_path, os.path.join(output_path, dest_path))


def save_txt_to_dir(output_path, dest_path, txt):
    """Save text to a directory, mimicking the interface of
    save_txt_zip."""
    save_txt(os.path.join(output_path, dest_path), txt)


def create_epub(input_path, output_path, unpacked=False):
    if os.path.isdir(output_path):
        shutil.rmtree(output_path)
    ensure_dirs(output_path)
    input_dirname = os.path.dirname(input_path)
    if unpacked:
        os.mkdir(output_path)
        copy = copy_file_to_dir
        save = save_txt_to_dir
    else:
        copy = copy_file_to_zip
        save = save_txt_zip

    # mimetype file
    copy(output_path, MIMETYPE_ORIGIN_PATH, MIMETYPE_DEST_PATH)

    # container.xml file
    container_template = load_txt(CONTAINER_ORIGIN_PATH)
    container_txt = chevron.render(
        container_template, {"package_path": PACKAGE_DEST_PATH}
    )
    save(output_path, CONTAINER_DEST_PATH, container_txt)

    # the SMIL and all the files referenced in the SMIL
    package_data = extract_files_from_SMIL(input_path)
    package_template = load_txt(PACKAGE_ORIGIN_PATH)
    package_txt = chevron.render(package_template, package_data)
    save(output_path, PACKAGE_DEST_PATH, package_txt)

    for entry in package_data["media"]:
        origin_path = os.path.join(input_dirname, entry["origin_path"])
        if not os.path.exists(origin_path):
            LOGGER.warning("Cannot find file %s to copy into EPUB file", origin_path)
            continue
        dest_path = os.path.join(EPUB_PATH, entry["dest_path"])
        copy(output_path, origin_path, dest_path)

    # CSS file
    copy(output_path, STYLESHEET_ORIGIN_PATH, STYLESHEET_DEST_PATH)
