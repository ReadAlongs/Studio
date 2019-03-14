#!/usr/bin/python

from os import environ, path
import argparse
from pocketsphinx import *
#from pocketsphinx.pocketsphinx import *
#from sphinxbase.sphinxbase import *

import flask
import redis

app = flask.Flask(__name__)
app.secret_key = 'asdf'
red = redis.StrictRedis()

def alert_stream(id):
    pubsub = red.pubsub()
    pubsub.subscribe('chat')
    for id in speech_to_id_stream():
        print id
        yield 'data: %s\n\n' % id

def speech_to_id_stream():
    MODELDIR = get_model_path()
    DATADIR = get_data_path()
    # Create a decoder with certain model
    config = Decoder.default_config()
    config.set_string('-hmm', path.join(MODELDIR, 'en-us'))
    #config.set_string('-lm', path.join(MODELDIR, 'en-us.lm.bin'))
    #config.set_string('-dict', path.join(MODELDIR, 'cmudict-en-us.dict'))

    config.set_string('-fsg', "s2.fsg")
    config.set_string('-dict', "s2.dict")
    # Decode streaming data.
    decoder = Decoder(config)

    print ("Pronunciation for word 'hello' is ", decoder.lookup_word("hello"))
    print ("Pronunciation for word 'abcdf' is ", decoder.lookup_word("abcdf"))

    decoder.start_utt()
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
                    new_seg = segs[-1]
                    if new_seg.word != '<sil>':
                        yield new_seg.word
              else:
                break
            break
    decoder.end_utt()

@app.route('/stream')
def stream():
    return flask.Response(event_stream(),
                          mimetype="text/event-stream")
                          

if __name__ == '__main__':
     parser = argparse.ArgumentParser(description='Convert XML to another orthography while preserving tags')
     #parser.add_argument('model', type=str, help='Model directory')
     #parser.add_argument('data', type=str, help='Data directory')
     args = parser.parse_args()
     speech_to_id_stream()
