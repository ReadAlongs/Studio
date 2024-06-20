(advanced-use)=

# Advanced topics

(adding-a-lang)=

## Adding a new language to g2p

If you want to align an audio book in a language that is not yet supported by
the g2p library, you will have to write your own g2p mapping for that language.

References:
: - The [g2p library](https://github.com/roedoejet/g2p) and its
    [documentation](https://g2p.readthedocs.io/).
  - The [7-part blog post on creating g2p mappings](https://blog.mothertongues.org/g2p-background/) on the [Mother Tongues Blog](https://blog.mothertongues.org/).

Once you have created a g2p mapping for your language, please consider
[contributing it to the project](https://blog.mothertongues.org/g2p-contributing/)
so others can also benefit from your work!

## Pre-processing your data

Manipulating the text and/or audio data that you are trying to align can
sometimes produce longer, more accurate ReadAlongs, that throw less
errors when aligning. While some of the most successful techniques we
have tried are outlined here, you may also need to customize your
pre-processing to suit your specific data.

### Audio pre-processing

#### Adding silences

Adding 1 second segments of silence in between phrases or paragraphs
sometimes improves the performance of the aligner. We do this using the
[Pydub](https://github.com/jiaaro/pydub) library which can be
pip-installed. Keep in mind that Pydub uses milliseconds.

If your data is currently 1 audio file, you will need to split it into
segments where you want to put the silences.

```
ten_seconds = 10 * 1000
first_10_seconds = soundtrack[:ten_seconds]
last_5_seconds = soundtrack[-5000:]
```

Once you have your segments, create an MP3 file containing only 1 second
of silence.

```
from pydub import AudioSegment

wfile = "appended_1000ms.mp3"
silence = AudioSegment.silent(duration=1000)
soundtrack = silence
```

Then you loop the audio files you want to append (segments and silence).

```
seg = AudioSegment.from_mp3(mp3file)
soundtrack = soundtrack + silence + seg
```

Write the soundtrack file as an MP3. This will then be the audio input
for your Read-Along.

```
soundtrack.export(wfile, format="mp3")
```

### Text pre-processing

#### Numbers

ReadAlong Studio cannot align numbers written as digits (ex. "123").
Instead, you will need to write them out (ex. "one two three" or "one
hundred and twenty three") depending on how they are read in your audio
file.

If you have lots of data, and the numbers are spoken in English (or any
of their supported languages), consider adding a library like
[num2words](https://github.com/savoirfairelinux/num2words) to your
pre-processing.

```
num2words 123456789
one hundred and twenty-three million, four hundred and fifty-six thousand, seven hundred and eighty-nine
```
