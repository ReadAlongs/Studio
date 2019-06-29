''' ReadAlong Studio web application views '''
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from flask import abort, flash, redirect, request, render_template, session
from werkzeug.utils import secure_filename

from readalongs.app import app

ALLOWED_TEXT = ['txt', 'xml', 'docx']
ALLOWED_AUDIO = ['wav', 'mp3']
ALLOWED_G2P = ['csv', 'xlsx']
ALLOWED_EXTENSIONS = set(ALLOWED_AUDIO + ALLOWED_G2P + ALLOWED_TEXT)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
# TODO: This is currently just uploading everything to tmp...this is not good. more sophisticated option is needed!
app.config['UPLOAD_FOLDER'] = '/tmp/rastudio'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.mkdir(app.config['UPLOAD_FOLDER'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def uploaded_files():
    upload_dir = Path(app.config['UPLOAD_FOLDER'])
    audio = list(upload_dir.glob('*.wav')) + list(upload_dir.glob('*.mp3'))
    text = list(upload_dir.glob('*.txt')) + \
        list(upload_dir.glob('*.xml')) + list(upload_dir.glob('*.docx'))
    maps = list(upload_dir.glob('*.csv')) + list(upload_dir.glob('*.xlsx'))
    return {'audio': [{'path': str(x), 'fn': os.path.basename(str(x))} for x in audio],
            'text': [{'path': str(x), 'fn': os.path.basename(str(x))} for x in text],
            'maps': [{'path': str(x), 'fn': os.path.basename(str(x))} for x in maps]}


@app.route('/')
def home():
    ''' Home View - go to Step 1 '''
    return redirect('/step/1')


@app.route('/step/<int:step>')
def steps(step):
    ''' Go through steps '''
    if step == 1:
        return render_template('upload.html', uploaded=uploaded_files())
    elif step == 2:
        return render_template('preview.html')
    elif step == 3:
        return render_template('export.html')
    else:
        abort(404)


@app.route('/step/1', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        if 'text' in request.files:
            # handle audio
            upfile = request.files['text']
        elif 'audio' in request.files:
            # handle audio
            upfile = request.files['audio']
        elif 'map' in request.files:
            # handle g2p
            upfile = request.files['map']
        else:
            flash('No file part')
            return redirect(request.url)
        filename = secure_filename(upfile.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        upfile.save(path)
        flash("File '%s' successfully uploaded" % filename)
        return redirect(request.url)

# with TemporaryDirectory() as tmpdir():

# fd, path = mkstemp()
#             try:
#                 document.save(path)
#                 return send_file(path,
#                                 as_attachment=True,
#                                 mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
#                                 attachment_filename='conjugations.docx')
#             finally:
#                 os.remove(path)
