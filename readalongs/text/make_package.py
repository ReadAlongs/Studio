###################################################
#
# make_package.py
#
# In order to facilitate easy packaging and deployment of readalongs,
# the make_package module takes a standard output directory from `readalongs align`
# and outputs a single html file with assets encoded using base64 in-line in the html.
#
# Note, this is not the optimal deployment. The ReadAlongs-WebComponent is already very portable
# and should be used directly as a webcomponent. However, in some situations a single-file
# is preferred as a low-cost, portable implementation.
#
#
###################################################

import os
from base64 import b64encode
from mimetypes import guess_type
from typing import Any

from lxml import etree

from readalongs._version import VERSION
from readalongs.log import LOGGER
from readalongs.text.util import parse_xml

JS_BUNDLE_URL = "https://unpkg.com/@readalongs/web-component@^1.4.0/dist/bundle.js"
FONTS_BUNDLE_URL = (
    "https://unpkg.com/@readalongs/web-component@^1.4.0/dist/fonts.b64.css"
)

BASIC_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=5.0">
  <meta name="application-name" content="read along">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=5.0">
  <meta name="generator" content="@readalongs/studio (cli) {studio_version}">
  <title>{title}</title>
  <script>{js}</script>
  <style attribution="See https://fonts.google.com/attribution for copyrights and font attribution">{fonts}</style>
</head>
<body>
    <read-along href="{ras}" audio="{audio}" theme="{theme}" use-assets-folder="false">
        <span slot='read-along-header'>{header}</span>
        <span slot='read-along-subheader'>{subheader}</span>
    </read-along>
</body>
</html>
"""


DEFAULT_TITLE = "ReadAlong-Studio for Interactive Storytelling"
DEFAULT_HEADER = "Your read-along title goes here"
DEFAULT_SUBHEADER = "Your read-along subtitle goes here"


def encode_from_path(path: str) -> str:
    """Encode file from bytes to b64 string with data and mime signature

    Args:
        path (str): path to file

    Returns:
        str: base64 string with data and mime signature
    """
    import requests  # Defer expensive import

    with open(path, "rb") as f:
        path_bytes = f.read()
    if str(path).endswith("xml") or str(path).endswith(".readalong"):
        root = parse_xml(path_bytes)
        for img in root.xpath("//graphic"):
            url = img.get("url")
            if url.startswith("http"):
                try:
                    request_result = requests.get(url)
                except requests.exceptions.RequestException:
                    request_result = None
            else:
                request_result = None
            mime = guess_type(url)
            if os.path.exists(url):
                with open(url, "rb") as f:
                    img_bytes = f.read()
                img_b64 = str(b64encode(img_bytes), encoding="utf8")
            elif request_result and request_result.status_code == 200:
                img_b64 = str(b64encode(request_result.content), encoding="utf8")
            else:
                LOGGER.warning(
                    f"The image declared at {url} could not be found. Please check that it exists or that the URL is valid."
                )
                continue
            img.attrib["url"] = f"data:{mime[0]};base64,{img_b64}"
        path_bytes = etree.tostring(root)
    b64 = str(b64encode(path_bytes), encoding="utf8")
    mime = guess_type(path)
    if str(path).endswith(
        ".m4a"
    ):  # hack to get around guess_type choosing the wrong mime type for .m4a files
        # TODO: Check other popular audio formats, .wav, .mp3, .ogg, etc...
        mime_type = "audio/mp4"
    if str(path).endswith(
        ".readalong"
    ):  # We declare it to be application/readalong+xml, not what mimetypes thinks
        mime_type = "application/readalong+xml"
    elif mime[0]:
        # Hack: until we properly extract audio from video files, force any video-based mime type to be read as audio
        mime_type = mime[0].replace("video", "audio")
    else:
        mime_type = "application"
        LOGGER.warning(
            f"We could not guess the mime type of file at {path}, we will try the generic mime type 'application', but this might not work with some files"
        )
    return f"data:{mime_type};base64,{b64}"


def create_web_component_html(
    ras_path: str,
    audio_path: str,
    title=DEFAULT_TITLE,
    header=DEFAULT_HEADER,
    subheader=DEFAULT_SUBHEADER,
    theme="light",
) -> str:
    import requests  # Defer expensive import

    try:
        js = requests.get(JS_BUNDLE_URL, timeout=10)
        js_status_code: Any = js.status_code
    except requests.exceptions.ReadTimeout as e:
        js_status_code = "TIMEOUT"
        LOGGER.warning(e)

    try:
        fonts = requests.get(FONTS_BUNDLE_URL, timeout=10)
        fonts_status_code: Any = fonts.status_code
    except requests.exceptions.ReadTimeout as e:
        LOGGER.warning(e)
        fonts_status_code = "TIMEOUT"

    if js_status_code != 200:
        LOGGER.warning(
            f"Sorry, the JavaScript bundle that is supposed to be at {JS_BUNDLE_URL} returned a {js_status_code}. Your ReadAlong will be bundled using a version that may not be up-to-date. Please check your internet connection."
        )
        with open(
            os.path.join(os.path.dirname(__file__), "bundle.js"), encoding="utf8"
        ) as f:
            js_raw = f.read()
    else:
        js_raw = js.text

    if fonts_status_code != 200:
        LOGGER.warning(
            f"Sorry, the fonts bundle that is supposed to be at {FONTS_BUNDLE_URL} returned a {fonts_status_code}. Your ReadAlong will be bundled using a version that may not be up-to-date. Please check your internet connection."
        )
        with open(
            os.path.join(os.path.dirname(__file__), "bundle.css"), encoding="utf8"
        ) as f:
            fonts_raw = f.read()
    else:
        fonts_raw = fonts.text

    return BASIC_HTML.format(
        ras=encode_from_path(ras_path),
        audio=encode_from_path(audio_path),
        js=js_raw,
        fonts=fonts_raw,
        title=title,
        header=header,
        subheader=subheader,
        theme=theme,
        studio_version=VERSION,
    )
