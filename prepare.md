---
title: 'Project documentation template'
disqus: hackmd
---

ReadAlong Studio Documentation
===

## Table of Contents

[TOC]

## Required knowledge
* git
* command line
* Audacity or similar
* Spinning up a server

## What you need to make a ReadAlong

In order to create a ReadAlong you will need two files:
* Plain text (`.txt`) or XML (`.xml`)
* Clear audio in any format supported by [ffmpeg](https://ffmpeg.org/ffmpeg-formats.html)

The content of the text file should be a transcription of the audio file.
The audio can be spoken or sung, but if there is background music or noise of any kind, the aligner is likely to fail. Clearly enunciated audio is also likely to increase accuracy.

There are also optional components you can add to enhance the experience of your ReadAlong:
* Images (formats??)
* 

## Command Line Interface (CLI)

The CLI has two main commands: `prepare` and `align`. If your data is a plain text file, you can run `prepare` to turn it into XML, where you can then modify the XML file before aligning it (do-not-align, ???).
Alternatively, if your plain text file does not need to be modified, you can run `align` and use one of the options to indicate that the input is plain text and not xml(???). 

#### `prepare`
Prepare a *.xml* file for `align` from a *.txt* file.

`readalongs prepare [options] [foo.txt] [foo.xml]`


##### `[foo.txt]`
Path to the plain text input file

The plain text file must be plain text encoded in `UTF-8` with one sentence per line. Paragraph breaks are marked by a blank line, and page breaks are marked by two blank lines.

##### `[foo.xml]`
Path to the XML output file, or - for stdout [default: `foo.xml`]


**Options (required marked by * ):**
`-d, --debug`                     
Add debugging messages to logger
`-f, --force-overwrite`           
Force overwrite output files
`*-l, --language`
Set language for input file

Languages currently supported:
`[alq|atj|ckt|crg-dv|crg-tmd|crj|crk|crl|crm|csw|ctp|dan|eng|fra|git|gla|iku|kkz|kwk-boas|kwk-napa|kwk-umista|lml|moh|oji|oji-syl|see|srs|str|tce|tgx|tli|und|win]`

`-h, --help`


So, a full command would be something like:

`readalongs prepare -l alq Studio/foo.txt Studio/foo.xml`

The generated xml will be parsed in to sentences. At this stage you can edit the xml to have any modifications, such as adding `do-not-align` as an attribute of any element in your xml.

##### `do-not-align`

There are two types of `do-not-align` (DNA): DNA audio and DNA text.

To use DNA text, simply add `do-not-align` as an attribute of any element in the xml (word, sentence, paragraph, or page).

###### Use cases for DNA

* Spoken introduction in the `.mp3` file that has no accompanying text


## Troubleshooting
Here are three types of common errors you may encounter when trying to run ReadAlongs, and ways to debug them.
### Phones missing in the acoustic model
You may get an error that looks like this:![](https://i.imgur.com/vKPhTud.png)
The general structure of your error would look like `Phone [character] is misig in the acoustic model; word [index] ignored`
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


* 




