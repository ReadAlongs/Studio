''' ReadAlong Studio web application views '''
from readalong_studio import app
from flask import abort, redirect, render_template, url_for

@app.route('/')
def home():
    ''' Home View - go to Step 1 '''
    print('hello')
    return redirect('/step/1')

@app.route('/step/<int:step>')
def step_one(step):
    ''' Go through steps '''
    if step == 1:
        return render_template('upload.html')
    elif step == 2:
        return render_template('preview.html')
    elif step == 3:
        return render_template('export.html')
    else:
        abort(404)
