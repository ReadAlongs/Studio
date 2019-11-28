#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# views.py
#
#   Views for ReadAlong Studio web application
#   Interactions are described as websocket events and responses
#   Corresponding JavaScript is found in readalongs/static/js/main.js
#
#######################################################################

import os
import io
from subprocess import run
from tempfile import mkdtemp

from pathlib import Path
from zipfile import ZipFile
from networkx import has_path
from flask_socketio import emit
from g2p.mappings.langs import LANGS_AVAILABLE, LANGS_NETWORK
from flask import abort, redirect, request, render_template, session, send_file, url_for

from datetime import datetime

from readalongs.app import app, socketio

# get the key from all networks in g2p module that have a path to 'eng-arpabet'
# which is needed for the readalongs
LANGS = [{'code': k, 'name': v} for x in LANGS_AVAILABLE
         for k, v in x.items()
         if LANGS_NETWORK.has_node(k) and has_path(LANGS_NETWORK, k, 'eng-arpabet')]

ALLOWED_TEXT = ['txt', 'xml', 'docx']
ALLOWED_AUDIO = ['wav', 'mp3']
ALLOWED_G2P = ['csv', 'xlsx']
ALLOWED_EXTENSIONS = set(ALLOWED_AUDIO + ALLOWED_G2P + ALLOWED_TEXT)


def allowed_file(filename: str) -> bool:
    """Determines whether filename is allowable
    
    Parameters
    ----------
    filename : str
        a filename

    Returns
    -------
    bool
        True if allowed
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def uploaded_files(dir_path: str) -> dict:
    """Returns all files that have been uploaded
    
    Parameters
    ----------
    dir_path : str
        path to directory where uploaded files are
    
    Returns
    -------
    dict
        A dictionary containing three keys:
            - audio : A list containing all paths to audio files
            - text  : A list containing all paths to text files
            - maps  : A list containing all paths to mapping files
    """
    upload_dir = Path(dir_path)
    audio = list(upload_dir.glob('*.wav')) + list(upload_dir.glob('*.mp3'))
    text = list(upload_dir.glob('*.txt')) + \
        list(upload_dir.glob('*.xml')) + list(upload_dir.glob('*.docx'))
    maps = list(upload_dir.glob('*.csv')) + list(upload_dir.glob('*.xlsx'))
    return {'audio': [{'path': str(x), 'fn': os.path.basename(str(x))} for x in audio],
            'text': [{'path': str(x), 'fn': os.path.basename(str(x))} for x in text],
            'maps': [{'path': str(x), 'fn': os.path.basename(str(x))} for x in maps]}


def update_session_config(**kwargs) -> dict:
    """Update the session configuration for running readalongs aligner.
    
    Parameters
    ----------
    **kwargs
        Arbitrary keyword arguments.

    Returns
    -------
    dict
        Returns the updated session configuration
    """
    previous_config = session.get('config', {})
    session['config'] = {**previous_config, **kwargs}
    return session['config']


@app.route('/')
def home():
    ''' Home View - go to Step 1 which is for uploading files '''
    return redirect(url_for('steps', step=1))


@socketio.on('config update event', namespace='/config')
def update_config(message):
    emit('config update response', {
         'data': update_session_config(**message)})


@socketio.on('upload event', namespace='/file')
def upload(message):
    if message['type'] == 'audio':
        save_path = os.path.join(session['temp_dir'], message['name'])
        session['audio'] = save_path
    if message['type'] == 'text':
        save_path = os.path.join(session['temp_dir'], message['name'])
        session['text'] = save_path
    if message['type'] == 'mapping':
        save_path = os.path.join(session['temp_dir'], message['name'])
        if 'config' in session and 'lang' in session['config']['lang']:
            del session['config']['lang']
        session['mapping'] = save_path
    with open(save_path, 'wb') as f:
        f.write(message['data']['file'])
    emit('upload response', {'data': {'path': save_path}})

# @SOCKETIO.on('remove event', namespace='/file')
# def remove_f(message):
#     path_to_remove = message['data']['path_to_remove']
#     if os.path.exists(path_to_remove) and os.path.isfile(path_to_remove):
#         os.remove(path_to_remove)
#     emit('remove response', {'data': {'removed_file': os.path.basename(path_to_remove)}})

# @SOCKETIO.on('upload event' namespace='file')
# def upload_f(message):


@app.route('/remove', methods=['POST'])
def remove_file():
    if request.method == 'POST':
        path = request.data.decode('utf8').split('=')[1]
        os.remove(path)
    return redirect(url_for('steps', step=1))


@app.route('/step/<int:step>')
def steps(step):
    ''' Go through steps '''
    if step == 1:
        session.clear()
        session['temp_dir'] = mkdtemp()
        temp_dir = session['temp_dir']
        return render_template('upload.html', uploaded=uploaded_files(temp_dir), maps=LANGS)
    elif step == 2:
        return render_template('preview.html')
    elif step == 3:
        timestamp = str(int(datetime.now().timestamp()))
        if not 'audio' in session or not 'text' in session:
            log = "Sorry, it looks like something is wrong with your audio or text. Please try again"
        else:
            flags = ['--force-overwrite']
            for option in ['--closed-captioning', '--save-temps', '--text-grid']:
                if session['config'].get(option, False):
                    flags.append(option)
            if session['text'].endswith('txt'):
                flags.append('--text-input')
                flags.append('--language')
                flags.append(session['config']['lang'])
            args = ['readalongs', 'align'] + flags + [session['text'],
                                                      session['audio'], os.path.join(session['temp_dir'], 'aligned' + timestamp)]
            fname, audio_ext = os.path.splitext(session['audio'])
            data = {'audio_ext': audio_ext}
            if session['config'].get('show-log', False):
                log = run(args, capture_output=True)
                data['log'] = log
            data['audio_path'] = os.path.join(
                session['temp_dir'], 'aligned' + timestamp + audio_ext)
            data['audio_fn'] = '/file/aligned' + timestamp + audio_ext
            data['text_path'] = os.path.join(
                session['temp_dir'], 'aligned' + timestamp + '.xml')
            data['text_fn'] = '/file/aligned' + timestamp + '.xml'
            data['smil_path'] = os.path.join(
                session['temp_dir'], 'aligned' + timestamp + '.smil')
            data['smil_fn'] = '/file/aligned' + timestamp + '.smil'
        return render_template('export.html', data=data)
    else:
        abort(404)


@app.route('/download', methods=['GET'])
def show_zip():
    files_to_download = os.listdir(session['temp_dir'])
    if not 'temp_dir' in session or not os.path.exists(session['temp_dir']) or not files_to_download or not any([x.startswith('aligned') for x in files_to_download]):
        return abort(404, "Nothing to download. Please go to Step 1 of the Read Along Studio")

    data = io.BytesIO()
    with ZipFile(data, mode='w') as z:
        for fname in files_to_download:
            print(fname)
            path = os.path.join(session['temp_dir'], fname)
            if fname.startswith('aligned'):
                print(path)
                z.write(path, fname)
    data.seek(0)

    if not data:
        return abort(400, "Invalid zip file")

    return send_file(
        data,
        mimetype='application/zip',
        as_attachment=True,
        attachment_filename='data_bundle.zip')


@app.route('/file/<string:fname>', methods=['GET'])
def return_temp_file(fname):
    path = os.path.join(session['temp_dir'], fname)
    if os.path.exists(path):
        return send_file(path)
    else:
        abort(404, "Sorry, we couldn't find that file.")
