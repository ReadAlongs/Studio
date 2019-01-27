#!/usr/bin/env python3
import fileinput

for line in fileinput.input():
    line = line.strip()
    if len(line) == 0 or line[0] == '#':
        print(line)
    else:
        code, phones = line.split('\t')
        print("%s\t%s\t%s" % (code, chr(int(code, 16)), phones))
