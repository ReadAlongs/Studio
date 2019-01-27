#!/usr/bin/env python3
import fileinput
from collections import defaultdict

phonelist = defaultdict(int)
for line in fileinput.input():
    line = line.strip()
    if len(line) == 0 or line[0] == '#':
        continue
    else:
        fields = line.split()
        code = fields[0]
        phones = fields[1:]
        for phone in phones:
            phonelist[phone] += 1

for phone in sorted(phonelist.keys()):
    print(phone)
