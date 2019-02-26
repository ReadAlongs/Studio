#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, division
from io import open
import logging, json, os
from mustache import render

from flask import Flask, request
app = Flask(__name__)

template = '''
<html>
  <body>
    <h1>Hello World</h1>
    <p>A {{data}} joint</p>
  </body>
</html>
'''

@app.route('/')
def hello_world():
    names = request.args.get("names")
    response = { "success": True,
                 "msg":'',
                 "data": " & ".join(names.split()) }
    return render(template, response)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5080)
