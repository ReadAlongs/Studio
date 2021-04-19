

---
---
title: 'ReadAlong Studio Documentation'
disqus: hackmd
---

ReadAlong Studio Documentation
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

## Installing
The best thing to do is install with pip: `pip install readalongs`.

Otherwise, clone the repo and pip install it locally.

```
$ git clone https://github.com/ReadAlongs/Studio.git
$ cd Studio
$ pip install -e .
```

If you don't already have it, you will also need [FFmpeg](https://ffmpeg.org/).

Windows: FFmpeg builds for Windows ([helpful instructions](https://windowsloop.com/install-ffmpeg-windows-10/))

Mac: `brew install ffmpeg`

Linux: `<your package manager> install ffmpeg`

On Windows, you might also need Visual Studio Build Tools (search for "Build Tools", select C++ when prompted) and swigwin. (TODO: verify whether these are still needed now that soundswallower has replaced pocketsphinx.)


## What you need to make a ReadAlong

In order to create a ReadAlong you will need two files:
* Plain text (`.txt`) or XML (`.xml`)
* Clear audio in any format supported by [ffmpeg](https://ffmpeg.org/ffmpeg-formats.html)

The content of the text file should be a transcription of the audio file.
The audio can be spoken or sung, but if there is background music or noise of any kind, the aligner is likely to fail. Clearly enunciated audio is also likely to increase accuracy.

## Command Line Interface (CLI)

The CLI has two main commands: `prepare` and `align`. If your data is a plain text file, you can run `prepare` to turn it into XML, where you can then modify the XML file before aligning it (do-not-align, ???).
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

##### Handling mismatches:`do-not-align`

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

`[output_base]`: path to the directory where the output files will be created as `output_base`*

 

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



