

---
---
Read-Along Studio User Guide
===

This library is an end-to-end audio/text aligner. It is meant to be used together with the ReadAlong-Web-Component to interactively visualize the alignment.

## Table of Contents

[TOC]


## Background

The concept is a web application with a series of stages of processing, which ultimately leads to a time-aligned audiobook - i.e. a package of:

* SMIL file describing time alignments
* XML file describing text
* Audio file (WAV or MP3)
* HTML file describing the web component

Which can be loaded using the [read-along web component](https://github.com/roedoejet/ReadAlong-Web-Component).

A book is generated as a standalone HTML page by default, but can optionally be generated as an ePub file.


## Required knowledge
* Command line interface (CLI)
* Plain text file/xml/smil
* Audacity or similar
* Spinning up a server


## What you need to make a ReadAlong

In order to create a ReadAlong you will need two files:
* Plain text (`.txt`) or XML (`.xml`)
* Clear audio in any format supported by [ffmpeg](https://ffmpeg.org/ffmpeg-formats.html)

The content of the text file should be a transcription of the audio file.
The audio can be spoken or sung, but if there is background music or noise of any kind, the aligner is likely to fail. Clearly enunciated audio is also likely to increase accuracy.


## Command Line Interface (CLI)

The CLI has two main commands: `prepare` and `align`. If your data is a plain text file, you can run `prepare` to turn it into XML, where you can then modify the XML file before aligning it
(e.g., to mark that some text is in a different language, to flag some do-not-align text, or to drop anchors in).
Alternatively, if your plain text file does not need to be modified, you can run `align` and use one of the options to indicate that the input is plain text and not xml: `-i`.

1. #### Getting from TXT to XML with `readalongs prepare`
Prepare a XML file for `align` from a TXT file.

`readalongs prepare [options] [story.txt] [story.xml]`



`[story.txt]`: path to the plain text input file (TXT)

`[story.xml]`: Path to the XML output file


The plain text file must be plain text encoded in `UTF-8` with one sentence per line. Paragraph breaks are marked by a blank line, and page breaks are marked by two blank lines.



| Options (required marked by * ) | |
| -------- | -------- |
| `*-l, --language`    | Set language for input file.
| `-d, --debug`    | Add debugging messages to logger
| `-f, --force-overwrite`    | Force overwrite output files (handy if youre troubleshooting and will be aligning repeatedly)
| `-h, --help`    | Displays CLI guide for `prepare`


The `*-l, --language` argument requires a language's 3 character [ISO code](https://en.wikipedia.org/wiki/ISO_639-3) as an argument.

Languages supported by RAS at the time of writing (run `readalongs prepare -h` to find out the current list):

`[alq|atj|ckt|crg-dv|crg-tmd|crj|crk|crl|crm|csw|ctp|dan|eng|fra|git|gla|iku|kkz|kwk-boas|kwk-napa|kwk-umista|lml|moh|oji|oji-syl|see|srs|str|tce|tgx|tli|und|win]`

So, a full command would be something like:

`readalongs prepare -l alq Studio/story.txt Studio/story.xml`

The generated XML will be parsed in to sentences. At this stage you can edit the XML to have any modifications, such as adding `do-not-align` as an attribute of any element in your XML.

##### Handling mismatches: `do-not-align`

There are two types of `do-not-align` (DNA): DNA audio and DNA text.

To use DNA text, simply add `do-not-align` as an attribute of any element in the xml (word, sentence, paragraph, or page).

    <w do-not-align="true" id="t0b0d0p0s0w0">dog</w>

If you have already run `readalongs prepare`, there will be documentation for DNA text in comments at the beginning of the generated xml file.

    <!-- To exclude any element from alignment, add the do-not-align="true" attribute to
         it, e.g., <p do-not-align="true">...</p>, or
         <s>Some text <foo do-not-align="true">do not align this</foo> more text</s> -->

To use DNA audio, you can specify a frame of time in milliseconds in the `config.json file` which you want the aligner to ignore.

    "do-not-align":
        {
        "method": "remove",
        "segments":
        [
            {
                "begin": 1,
                "end": 17000
            }
        ]
        }

###### Use cases for DNA

* Spoken introduction in the audio file that has no accompanying text (DNA audio)
* Text that has no matching audio, such as credits/acknowledgments (DNA text)



2. #### Aligning your text and audio with `readalongs align`

Align a text file (XML or TXT) and an audio file to create a time-aligned audiobook.


`readalongs align [options] [story.txt/xml] [story.mp3/wav] [output_base]`

`[story.txt/xml] `: path to the text file (TXT or XML)

`[story.mp3/wav] `: path to the audio file (MP3, WAV or any format supported by ffmpeg)

`[output_base]`: path to the directory where the output files will be created as `output_base*`



| Options (required marked by * ) |  |
| -------- | -------- |
| `*-l, --language`    | Set language for input file (\*required if input is pain text)
|`b, --bare` | Bare alignments: do not split silences between words
|`-c, --config PATH`| Use ReadAlong-Studio configuration file (in JSON format)
|`-C, --closed-captioning`| Export sentences to WebVTT and SRT files
|`-i, --text-input`| Input is plain text (TXT) (otherwise it's assumed to be XML)
|`-u, --unit [w|m]`| Unit (w = word, m = morpheme) to align to
|`-t, --text-grid`|Export to Praat TextGrid & ELAN eaf file
|`-x, --output-xhtml`| Output simple XHTML instead of XML
| `-d, --debug`| Add debugging messages to logger
|`-s, --save-temps`|  Save intermediate stages of processing and temporary files (dictionary, FSG, tokenization, etc.)
| `-f, --force-overwrite`    | Force overwrite output files (handy if you're troubleshooting and will be aligning repeatedly)
| `-h, --help`    |Displays CLI guide for `align`


See above for more information on the `*-l, --language` argument.

A full command would be something like:

`readalongs align -l alq -f -c Studio/story.xml Studio/story.mp3 Studio/story/aligned`

### The `config.json` file

Create a JSON file called `config.json` in the same folder as your other ReadAlong input files. The config file currently accepts two components: adding images to your ReadAlongs, and DNA audio (see above add hyperlink).

To add images, simply indicate the page number as the key, and the name of the image file as the value, as an entry in the `"images"` dictionary.

```
{ "images": { "0": "p1.jpg", "1": "p2.jpg" } }
```

The image has to be a JPEG (`.jpg`) file (check which formats are supported!!!).

Both images and DNA audio can be specified in the same config file, such as in the example below:

```
{
    "images":
        {
            "0": "image-for-page1.jpg",
            "1": "image-for-page1.jpg",
            "2": "image-for-page2.jpg",
            "3": "image-for-page3.jpg"
        },

    "do-not-align":
        {
        "method": "remove",
        "segments":
            [
                {   "begin": 1,     "end": 17000   },
                {   "begin": 57456, "end": 68000   }
            ]
        }
}
```

Warning: mind your commas! The JSON format is very picky: commas separate elements in a list or dictionnary, but if you accidentally have a comma after the last element (e.g., by cutting and pasting whole lines), you will get a syntax error.

## Pre-processing your data

Manipulating the text and/or audio data that you are trying to align can sometimes produce longer, more accurate ReadAlongs, that throw less errors when aligning. While some of the most successful techniques we have tried are outlined here, you may also need to customize your pre-processing to suit your specific data.

### Audio pre-processing

#### Adding silences

Adding 1 second segments of silence in between phrases or paragraphs sometimes improves the performance of the aligner. We do this using the [Pydub](https://github.com/jiaaro/pydub) library which can be pip-installed. Keep in mind that Pydub uses milliseconds.

If your data is currently 1 audio file, you will need to split it into segments where you want to put the silences.

```
ten_seconds = 10 * 1000
first_10_seconds = soundtrack[:ten_seconds]
last_5_seconds = soundtrack[-5000:]

```
Once you have your segments, create an MP3 file containing only 1 second of silence.

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
Write the soundtrack file as an MP3. This will then be the audio input for your Read-Along.

```
soundtrack.export(wfile, format="mp3")
```

### Text pre-processing

#### Numbers

ReadAlong Studio cannot align numbers written as digits (ex. "123"). Instead, you will need to write them out (ex. "one two three" or "one hundred and twenty three") depending on how they are read in your audio file.

If you have lots of data, and the numbers are spoken in English (or any of their supported languages), consider adding a library like [num2words](https://github.com/savoirfairelinux/num2words) to your pre-processing.

```
num2words 123456789
one hundred and twenty-three million, four hundred and fifty-six thousand, seven hundred and eighty-nine

```


## Troubleshooting
Here are three types of common errors you may encounter when trying to run ReadAlongs, and ways to debug them.
### Phones missing in the acoustic model
You may get an error that looks like this:![](https://i.imgur.com/vKPhTud.png)
The general structure of your error would look like `Phone [character] is missing in the acoustic model; word [index] ignored`
This error is most likely caused not by a bug in your ReadAlong input files, but by an error in one of your g2p mappings. The error message is saying that there is a character in your ReadAlong text that is not being properly converted to English-arpabet (eng-arpabet), which is the language ReadAlong uses to map text to sound. Thus, ReadAlong cannot match your text to a corresponding sound (phone) in your audio file because it cannot understand what sound the text is meant to represent. Follow these steps to debug the issue **in g2p**.

1. Identify which characters in each line of the error message are **not** being converted to eng-arpabet. These will either be:

    a. characters that are not in caps  (for example `g` in the string `gUW` in the error message shown above.)
    b. a character not traditionally used in English (for example é or Ŧ, or `ʰ` in the error message shown above.)

  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;You can confirm you have isolated the right characters by ensuring &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;every other character in your error message appears as an **output** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;in the [eng-ipa-to-arpabet mapping](https://github.com/roedoejet/g2p/blob/master/g2p/mappings/langs/eng/eng_ipa_to_arpabet.json). These are the problematic &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;characters we need to debug in the error message shown above: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`g` and `ʰ`.

  2. Once you have isolated the characters that are not being converted to eng-arpabet, you are ready to begin debugging the issue. Go through steps 3 - ? for each problematic character.
  3. Our next step is to identify which mapping is converting the problematic characters incorrectly. Most of the time, the issue will be in either the first or the second of the following mappings:
      i.  *xyz-ipa* (where xyz is the ISO language code for your mapping)
      ii. *xyz-equiv* (if you have one)
      iii. *xyz-ipa_to_eng-ipa* (this mapping  must be generated automatically in g2p. Refer //here_in_the_guide to see how to do this.)
      iv. [*eng-ipa-to-arpabet mapping*](https://github.com/roedoejet/g2p/blob/master/g2p/mappings/langs/eng/eng_ipa_to_arpabet.json) (The issue is rarely found here, but it doesn't hurt to check.)
4. Find a word in your text that uses the problematic character. For the sake of example, let us assume the character I am debugging is `g`, that appears in the word "dog", in language "xyz".
5. Make sure you are in the g2p repository and run the word through `g2p convert` to confirm you have isolated the correct characters to debug: `g2p convert dog xyz eng-arpabet`. Best practice is to copy+paste the word directly from your text instead of retyping it. Make sure to use the ISO code for your language in place of "xyz".
     *If the word converts cleanly into eng-arpabet characters, your issue does not lie in your mapping. //Refer to other potential RA issues*

6. From the result of the command run in 5, note the characters that do **not** appear as **inputs** in the [eng-ipa-to-arpabet mapping](https://github.com/roedoejet/g2p/blob/master/g2p/mappings/langs/eng/eng_ipa_to_arpabet.json). These are the characters that have not been converted into characters that eng-ipa-to-arpabet can read. These should be the same characters you identified in step 2.

7. Run `g2p convert dog xyz xyz-ipa`. Ensure the result is what you expect. If not, your error may arise from a problem in this mapping. refer_to_g2p_troubleshooting. If the result is what you expect, continue to the next step.
8. Note the result from running the command in 7. Check that the characters (appear/being mapped by generated -- use debugger or just look at mapping)

### g2p cascade

Sometimes the g2p conversion of the input text will not succeed, for various reasons. A word might use characters not recognized by the g2p for the language, or it might be in a different language. Whatever the reason, the output for the g2p conversion will not be valid ARPABET, and so the system will not be able to proceed to alignment by SoundSwallower.

If you know the language for that text, you can mark it as such in the xml. E.g., `<s xml:lang="eng">This sentence is in English.</s>`. The `xml:lang` attribute can be added to any element in the XML structure and will apply to text at any depth within that element, unless the attribute is specified again at a deeper level, e.g., `<s xml:lang="eng">English mixed with <foo xml:lang="fra">français</foo>.</s>`.

There is also a simpler option available: the g2p cascade. When the g2p cascade is enabled, the g2p mapping will be done by first trying the language specified in the XML file (or with the `-l` flag on the command line, if the input is plain text). For each word where the result is not valid ARPABET, the g2p mapping will be attempted again with each of the languages specified in the g2p cascade, in order, until a valid ARPABET conversion is obtained. If not valid conversion is possible, are error message is printed and alignment is not attempted.

To enable the g2p cascade, add the `--g2p-fallback l1:l2:...` option to `readalongs g2p` or `readalongs align`:
```
readalongs g2p --g2p-fallback fra:eng:und myfile.tokenize.xml myfile.g2p.xml
readalongs align --g2p-fallback fra:eng:und myfile.xml myfile.wav output
```

#### "Undetermined" language code: `und`

Notice that the two examples use `und` as the last language in the cascade. `und`, for Undetermined, is a special language mapping that uses the Unicode definition of all know characters in all alphabets, and maps them as if the name of that character was how it is pronounced. While crude, this mapping works surprisingly well for the purposes of forced alignment, and allows `readalongs align` to successfully align most text with a few foreign words without any manual intervention. We recommend systematically using `und` at the end of the cascade. Note that adding another language after `und` will have no effect, since the Undetermined mapping will map any string to valid ARPABET.

#### Debugging g2p mapping issues

The warning messages issued by `readalongs g2p` and `readalongs align` indicate which words are causing g2p problems. It can be worth inspecting to input text to fix any encoding or spelling errors highlighted by these warnings. More detailed messages can be produced by adding the `--g2p-verbose` switch, to obtain a lot more information about g2p'ing words in each language g2p was unsucessfully attempted.

### Breaking up the pipeline

A new command was recently added to the CLI: `readalongs g2p`, to break processing up.

The following series of commands:
```
readalongs prepare -l lang  file.txt file.xml
readalongs tokenize file.xml file.tokenized.xml
readalongs g2p file.tokenized.xml file.g2p.xml
readalongs align file.g2p.xml file.wav output
```
is equivalent to the single command:
```
readalongs align -l lang file.txt file.wav output
```
except that when running the pipeline as four separate commands, you can edit the XML files between each step to make any required adjustments and corrections.

### Anchors: marking known alignment points

Long audio/text file pairs can sometimes be difficult to align correctly, because the aligner might get lost part way through the alignment process. Anchors can be used to tell the aligner about known correspondance points between the text and the audio stream.

#### Anchor syntax

Anchors are inserted in the XML file (the output of `readalongs prepare`, `readalongs tokenize` or `readalongs g2p`) using the following syntax: `<anchor time="3.42s"/>` or `<anchor time="3420ms"/>`. The time can be specified in seconds (this is the default) or milliseconds.

Anchors can be placed anywhere in the XML file: between/before/after any element or text.

Example:
```
<?xml version='1.0' encoding='utf-8'?> <TEI> <text xml:lang="eng"> <body>
    <anchor time="143ms"/>
    <div type="page">
    <p>
        <s>Hello.</s>
        <anchor time="1.62s"/>
        <s>This is <anchor time="3.81s"/> <anchor time="3.94s"/> a test</s>
        <s><anchor time="4123ms"/>weirdword<anchor time="4789ms"/></s>
    </p>
    </div>
    <anchor time="6.74s"/>
</body> </text> </TEI>
```

#### Anchor semantics

When anchors are used, the alignment task is divided at each anchor, creating a series of segments that are aligned independently from one another. When alignment is performed, the aligner sees only the audio and the text from the segment being processed, and the results are joined together afterwards.

The beginning and end of files are implicit anchors: *n* anchors define *n+1* segments: from the beginning of the audio and text to the first anchor, between pairs of anchors, and from the last anchor to the end of the audio and text.

Special cases equivalent to do-not-align audio:
 - If an anchor occurs before the first word in the text, the audio up to that anchor's timestamps is excluded from alignment.
 - If an anchor occurs after the last word, the end of the audio is excluded from alignment.
 - If two anchors occur one after the other, the time span between them in the audio is excluded from alignment.
Using anchors to define do-not-align audio segments is effectively the same as marking them as "do-not-align" in the `config.json` file, except that DNA segments declared using anchors have a known alignment with respect to the text, while the position of DNA segments declared in the config file are inferred by the aligner.

#### Anchor use cases

1. Alignment fails because the stream is too long or too difficult to align:

   When alignment fails, listen to the audio stream and try to identify where some words you can pick up start or end. Even if you don't understand the language, there might be some words you're able to pick up and use as anchors to help the aligner.

2. You already know where some words/sentences/paragraphs start or end, because the data came with some partial alignment information. For example, the data might come from an ELAN file with sentence alignments.

   These known timestamps can be converted to anchors.
