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
from typing import Any, Union

from lxml import etree

from readalongs._version import VERSION
from readalongs.log import LOGGER
from readalongs.text.util import parse_xml

JS_BUNDLE_URL = "https://unpkg.com/@readalongs/web-component@^1.5.2/dist/bundle.js"
FONTS_BUNDLE_URL = (
    "https://unpkg.com/@readalongs/web-component@^1.5.2/dist/fonts.b64.css"
)

BASIC_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=5.0">
  <meta name="application-name" content="read along">
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


def encode_from_path(path: Union[str, os.PathLike]) -> str:
    """Encode file from bytes to b64 string with data and mime signature

    Args:
        path: path to file

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


def fetch_bundle_file(url, filename, prev_status_code):
    """Fetch either of the online bundles, or their on-disk fallback if needed."""
    import requests  # Defer expensive import

    # Don't try again from the web if if failed last time in the same process
    # This matters when a client uses the convert_prealigned_text_to_offline_html
    # endpoint in api.py, we don't want them to wait many times for the same
    # download attempt to fail when, e.g., they don't have web access enabled.
    if prev_status_code in (None, 200):
        try:
            get_result = requests.get(url, timeout=5)
            status_code: Any = get_result.status_code
        except requests.exceptions.RequestException as e:
            LOGGER.warning(e)
            status_code = type(e).__name__
        if status_code != 200:  # pragma: no cover
            LOGGER.warning(
                f"Sorry, the JavaScript or fonts bundle that is supposed to be at {url} returned a {status_code}. Your ReadAlong will be bundled using a version that may not be up-to-date. Please check your internet connection."
            )
    else:
        status_code = prev_status_code

    if status_code != 200:
        with open(
            os.path.join(os.path.dirname(__file__), filename), encoding="utf8"
        ) as f:
            file_contents = f.read()
    else:
        file_contents = get_result.text
    return status_code, file_contents


_prev_js_status_code: Any = None
_prev_fonts_status_code: Any = None


def create_web_component_html(
    ras_path: Union[str, os.PathLike],
    audio_path: Union[str, os.PathLike],
    title=DEFAULT_TITLE,
    header=DEFAULT_HEADER,
    subheader=DEFAULT_SUBHEADER,
    theme="light",
) -> str:
    global _prev_js_status_code
    _prev_js_status_code, js_raw = fetch_bundle_file(
        JS_BUNDLE_URL, "bundle.js", _prev_js_status_code
    )

    global _prev_fonts_status_code
    if _prev_fonts_status_code is None and _prev_js_status_code != 200:
        # If fetching bundle.js failed, don't bother trying bundle.css
        _prev_fonts_status_code = _prev_js_status_code
    _prev_fonts_status_code, fonts_raw = fetch_bundle_file(
        FONTS_BUNDLE_URL, "bundle.css", _prev_fonts_status_code
    )

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
