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
import re
from base64 import b64encode
from mimetypes import guess_type
from textwrap import indent
from typing import Any, Union

from lxml import etree

from readalongs._version import VERSION
from readalongs.log import LOGGER
from readalongs.text.util import CURRENT_WEB_APP_VERSION, parse_xml

JS_BUNDLE_URL = f"https://unpkg.com/@readalongs/web-component@^{CURRENT_WEB_APP_VERSION}/dist/bundle.js"
FONTS_BUNDLE_URL = f"https://unpkg.com/@readalongs/web-component@^{CURRENT_WEB_APP_VERSION}/dist/fonts.b64.css"

# Template for the Offline HTML file
BASIC_HTML = """
<!DOCTYPE html>

<!--

                    Instructions for Opening this File

This is a read-along file that can be opened in a web browser without
requiring Internet access.

If you see this text, you probably downloaded a ReadAlong HTML file from a
cloud storage service, and it's showing you the raw contents instead of
displaying your readalong.

To view the file:

1. Download the file to your computer -- there should be a download button
    visible or hidden in the three dot menu in your cloud storage service.

2. Once downloaded, open the file in a web browser. You can do this by
    double-clicking it in your file explorer or in your browser's downloaded
    files list.

-->

<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=5.0">
    <meta name="application-name" content="read along">
    <meta name="generator" content="@readalongs/studio (cli) {studio_version}">
    <title>{title}</title>
    <script name="@readalongs/web-component" version="{js_version}">
{js}
    </script>
    <style attribution="See https://fonts.google.com/attribution for copyrights and font attribution">
{fonts}
    </style>
  </head>
  <body>
    <read-along
      href="{ras}"
      audio="{audio}"
      theme="{theme}"
      use-assets-folder="false"
    >
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


def extract_version_from_url(url: str) -> str:
    """Extract the version from a URL string."""

    match = re.search(r"@(\d+\.\d+\.\d+)", url)
    if match:
        return match.group(1)
    else:
        LOGGER.warning(f"Could not extract bundle version from URL: {url}")
        return "unknown"


FETCH_BUNDLE_TIMEOUT_SECONDS = 10


def fetch_bundle_file(url: str, filename: str, prev_status_code: Any):
    """Fetch either of the online bundles, or their on-disk fallback if needed."""
    import requests  # Defer expensive import

    # Don't try again from the web if if failed last time in the same process
    # This matters when a client uses the convert_prealigned_text_to_offline_html
    # endpoint in api.py, we don't want them to wait many times for the same
    # download attempt to fail when, e.g., they don't have web access enabled.
    if prev_status_code in (None, 200):
        try:
            get_result = requests.get(url, timeout=FETCH_BUNDLE_TIMEOUT_SECONDS)
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
            bundle_version = "unknown"
    else:
        file_contents = get_result.text
        bundle_version = extract_version_from_url(get_result.url)
    return status_code, file_contents, bundle_version


_prev_js_status_code: Any = None
_prev_fonts_status_code: Any = None
# Cache the bundle contents so we don't fetch it more than once when running a process
# that might generate several HTML files via the API, e.g., the EveryVoice demo app.
js_bundle_contents = None
js_bundle_version = None
fonts_bundle_contents = None


def create_web_component_html(
    ras_path: Union[str, os.PathLike],
    audio_path: Union[str, os.PathLike],
    title=DEFAULT_TITLE,
    header=DEFAULT_HEADER,
    subheader=DEFAULT_SUBHEADER,
    theme="light",
) -> str:
    global _prev_js_status_code, js_bundle_contents, js_bundle_version
    if js_bundle_contents is None:
        _prev_js_status_code, js_bundle_contents, js_bundle_version = fetch_bundle_file(
            JS_BUNDLE_URL, "bundle.js", _prev_js_status_code
        )
        js_bundle_contents = indent(js_bundle_contents, " " * 6)

    global fonts_bundle_contents
    if fonts_bundle_contents is None:
        global _prev_fonts_status_code
        if _prev_fonts_status_code is None and _prev_js_status_code != 200:
            # If fetching bundle.js failed, don't bother trying bundle.css
            _prev_fonts_status_code = _prev_js_status_code
        _prev_fonts_status_code, fonts_bundle_contents, _ = fetch_bundle_file(
            FONTS_BUNDLE_URL, "bundle.css", _prev_fonts_status_code
        )
        fonts_bundle_contents = indent(fonts_bundle_contents, " " * 6)

    return BASIC_HTML.format(
        ras=encode_from_path(ras_path),
        audio=encode_from_path(audio_path),
        js=js_bundle_contents,
        js_version=js_bundle_version,
        fonts=fonts_bundle_contents,
        title=title,
        header=header,
        subheader=subheader,
        theme=theme,
        studio_version=VERSION,
    )
