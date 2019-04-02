#!/usr/bin/env python3

##################################################
#
# app.py
#
##################################################

from __future__ import print_function, division
from io import open
import logging, argparse, os
from lxml import etree
import mustache
import webbrowser

try:
    unicode()
except:
    unicode = str

import datetime
import flask
import redis
import mustache
import time

from os import environ, path
from pocketsphinx import *

app = flask.Flask(__name__)

SSE_TEMPLATE = '''
retry: 50
data: {{data}}

'''

def event_stream(decoder):

    for id in speech_to_id_stream(decoder):
        data = { "data": id }
        yield mustache.render(SSE_TEMPLATE, data)

def speech_to_id_stream(decoder):

    #stream = open("s2.wav", 'rb')

    buf = bytearray(2048)
    audio_device = Ad(None, 16000)

    current_len_segs = 0
    with audio_device:
        while True:
            while audio_device.readinto(buf) >= 0:
              if buf:
                decoder.process_raw(buf, False, False)
                segs = list(decoder.seg())
                if len(segs) > current_len_segs:
                    current_len_segs = len(segs)
                    for new_seg in segs:
                        yield new_seg.word
              else:
                break
            break


@app.route("/stream")
def stream():
    return flask.Response(event_stream(decoder), mimetype="text/event-stream")


TEMPLATE = '''
<!doctype html>
<title>chat</title>
<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js"></script>
<style>body { max-width: 500px; margin: auto; padding: 5px; background: black; color: #fff; font-size: 18pt;}</style>
<p>Try saying this out loud:</p>
<p>
{{#words}}
    <span id="{{id}}">{{text}}</span>
{{/words}}
</p>
<script>
    function sse() {
        var source = new EventSource('/stream');
        var out = document.getElementById('out');
        source.onmessage = function(e) {
            if (e.data == '&lt;sil&gt;') {
                return;
            }
            console.log("#"+e.data);
            $("#"+e.data).css('color', 'red');
        };
    }
    sse();
</script>
'''

page_data = {}

@app.route('/')
def home():
    return mustache.render(TEMPLATE, page_data)

def go(xml_path, fsg_path, dct_path):
    global decoder, page_data
    MODELDIR = get_model_path()
    config = Decoder.default_config()
    config.set_string('-hmm', os.path.join(MODELDIR, 'en-us'))
    #config.set_string('-lm', path.join(MODELDIR, 'en-us.lm.bin'))
    #config.set_string('-dict', path.join(MODELDIR, 'cmudict-en-us.dict'))

    config.set_string('-fsg', fsg_path)
    config.set_string('-dict', dct_path)
    # Decode streaming data.
    decoder = Decoder(config)
    decoder.start_utt()

    page_data = { "words": [] }
    with open(xml_path, "r", encoding="utf-8") as fin:
        xml = etree.fromstring(fin.read())
        for word in xml.xpath(".//w"):
            page_data["words"].append({
                "id": word.attrib["id"],
                "text": word.text
            })

    url = "http://127.0.0.1:5000/"
    webbrowser.open_new_tab(url)
    app.run(debug=False, host='0.0.0.0', port=5000)
    #decoder.end_utt()

if __name__ == '__main__':
     parser = argparse.ArgumentParser(description='Craaaaaaaaaaaaazy')
     parser.add_argument('text', type=str, help='TEI XML format')
     parser.add_argument('fsg', type=str, help='FSG file')
     parser.add_argument('dict', type=str, help='FSG file')
     args = parser.parse_args()
     go(args.text, args.fsg, args.dict)
