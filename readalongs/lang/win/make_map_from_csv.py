#!/usr/bin/env python3

import csv
import fileinput

reader = csv.reader(fileinput.input())
for wisconsin, nebraska, ipa in reader:
    ipa = ipa.split(', ')[0]  # take the first one
    print('    { "in": "%s", "out": "%s" },'
          % (wisconsin, ipa))
    if nebraska != wisconsin:
        print('    { "in": "%s", "out": "%s" },'
              % (nebraska, ipa))
    
