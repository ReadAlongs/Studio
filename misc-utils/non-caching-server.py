#!/usr/bin/env python3

# This script is copied and modified from
# https://github.com/python/cpython/blob/3.9/Lib/http/server.py
# The original script is Copyright (c) Python Software Foundation and licensed
# under the Python Software Foundation License Version 2.
# See https://github.com/python/cpython/blob/main/LICENSE for the full details.

# The modification made at National Research Council Canada are released under
# the MIT License.

# MIT License
#
# Copyright (c) 2021, National Research Council Canada (only for the NRC
# modifications to this script)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Description of modifications by NRC
# - Eddie Antonio Santos, 2021: extract the minimum http server code and modify
#   it to disable client-side caching by systematically adding the header
#       Cache-Control: no-store, max-age=0
#   to all requests.
#   This is to work around an issue on Mac computers where sometimes even a hard
#   refresh will not fetch manually updated pages.

import contextlib
import os
import socket
import urllib
from functools import partial
from http import HTTPStatus
from http.server import test  # type: ignore
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class NonCachingHTTPRequestHandler(SimpleHTTPRequestHandler):
    """
    Same as SimpleHTTPRequestHandler, but instructs the browser to never cache!
    """

    def send_caching_headers(self):
        """
        See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control#cacheability
        """
        self.send_header("Cache-Control", "no-store, max-age=0")

    # copy-pasted from: https://github.com/python/cpython/blob/3.9/Lib/http/server.py
    # changed:
    #  - self.send_caching_headers
    def send_head(self):
        """Common code for GET and HEAD commands.
        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith("/"):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + "/", parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        # check for trailing "/" which should return 404. See Issue17324
        # The test for this was added in test_httpserver.py
        # However, some OS platforms accept a trailingSlash as a filename
        # See discussion on python-dev and Issue34711 regarding
        # parseing and rejection of filenames with a trailing slash
        if path.endswith("/"):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(fs[6]))
            self.send_caching_headers()
            self.end_headers()
            return f
        except:  # noqa E722
            f.close()
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bind",
        "-b",
        metavar="ADDRESS",
        help="Specify alternate bind address " "[default: all interfaces]",
    )
    parser.add_argument(
        "--directory",
        "-d",
        default=os.getcwd(),
        help="Specify alternative directory " "[default:current directory]",
    )
    parser.add_argument(
        "port",
        action="store",
        default=8000,
        type=int,
        nargs="?",
        help="Specify alternate port [default: 8000]",
    )
    args = parser.parse_args()
    handler_class = partial(NonCachingHTTPRequestHandler, directory=args.directory)

    # ensure dual-stack is not disabled; ref #38907
    class DualStackServer(ThreadingHTTPServer):
        def server_bind(self):
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

    test(
        HandlerClass=handler_class,
        ServerClass=DualStackServer,
        port=args.port,
        bind=args.bind,
    )
