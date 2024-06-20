(cli-guide)=

# Command line interface (CLI) user guide

This page contains guidelines on using the ReadAlongs CLI. See also
{ref}`cli-ref` for the full CLI reference.

The ReadAlongs CLI has two main commands: `readalongs make-xml` and
`readalongs align`.

- If your data is a plain text file, you can run `make-xml` to turn
  it into ReadAlongs XML, which you can then align with
  `align`. Doing this in two steps allows you to modify the XML file
  before aligning it (e.g., to mark that some text is in a different
  language, to flag some do-not-align text, or to drop anchors in).
- Alternatively, if your plain text file does not need to be modified, you can
  run `align` directly on it, since it also accepts plain text input.  You'll
  need the `-l <language(s)>` option to indicate what language your text is in.

Two additional commands are sometimes useful: `readalongs tokenize` and
`readalongs g2p`.

- `tokenize` takes the output of `make-xml` and tokenizes it, wrapping each
  word in the text in a `<w>` element.
- `g2p` takes the output of `tokenize` and mapping each word to its
  phonetic transcription using the g2p library. The phonetic transcription is
  represented using the ARPABET phonetic codes and are added in the `ARPABET`
  attribute to each `<w>` element.

The result of `tokenize` or `g2p` can be fixed manually if necessary and
then used as input to `align`.

## Getting from TXT to XML with readalongs make-xml

Run {ref}`cli-make-xml` to make the ReadAlongs XML file for `align` from a TXT file.

`readalongs make-xml [options] [story.txt] [story.readalong]`

`[story.txt]`: path to the plain text input file (TXT)

`[story.readalong]`: Path to the XML output file

The plain text file must be plain text encoded in `UTF-8` with one
sentence per line. Paragraph breaks are marked by a blank line, and page
breaks are marked by two blank lines.

| Key Options                    | Option descriptions                                                                                                   |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `-l, --language(s)` (required) | The language code for story.txt. Specifying multiple comma- or colon-separated languages triggers {ref}`g2p-cascade`. |
| `-f, --force-overwrite`        | Force overwrite output files (handy if you're troubleshooting and will be aligning repeatedly)                        |
| `-h, --help`                   | Displays CLI guide for `make-xml`                                                                                     |

The `-l, --language` argument requires a language’s 3 character [ISO
code](https://en.wikipedia.org/wiki/ISO_639-3) as an argument.

The languages supported by RAS can be listed by running `readalongs make-xml -h`
and they can also be found in the {ref}`cli-make-xml` reference.

So, a full command for a story in Algonquin, with an implicit g2p fallback to
Undetermined, would be something like:

`readalongs make-xml -l alq Studio/story.txt Studio/story.readalong`

The generated XML will be parsed in to sentences. At this stage you can
edit the XML to have any modifications, such as adding `do-not-align`
as an attribute of any element in your XML.

The format of the generated XML is based on \[TEI
Lite\](<https://tei-c.org/guidelines/customization/lite/>) but is
considerably simplified.  The DTD (document type definition) can be
found in the ReadAlong Studio source code under
`readalongs/static/read-along-1.0.dtd`.

(dna)=

### Handling mismatches: do-not-align

There are two types of "do-not-align" (DNA) content: DNA audio and DNA text.

To use DNA text, add `do-not-align` as an attribute to any
element in the xml (word, sentence, paragraph, or page).

```
<w do-not-align="true" id="t0b0d0p0s0w0">dog</w>
```

If you have already run `readalongs make-xml`, there will be
documentation for DNA text in comments at the beginning of the generated
xml file.

```
<!-- To exclude any element from alignment, add the do-not-align="true" attribute to
     it, e.g., <p do-not-align="true">...</p>, or
     <s>Some text <foo do-not-align="true">do not align this</foo> more text</s> -->
```

To use DNA audio, you can specify a timeframe in milliseconds in the
`config.json` file which you want the aligner to ignore.

```
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
```

#### Use cases for DNA

- Spoken introduction in the audio file that has no accompanying text
  (DNA audio)
- Text that has no matching audio, such as credits/acknowledgments (DNA
  text)

## Aligning your text and audio with readalongs align

Run {ref}`cli-align` to align a text file (RAS or TXT) and an audio file to
create a time-aligned audiobook.

`readalongs align [options] [story.txt/xml] [story.mp3/wav] [output_base]`

`[story.txt/ras]`: path to the text file (TXT or RAS)

`[story.mp3/wav]`: path to the audio file (MP3, WAV or any format
supported by ffmpeg)

`[output_base]`: path to the directory where the output files will be
created, as `output_base*`

| Key Options             | Option descriptions                                                                                                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `-l, --language(s)`     | The language code for story.txt. Specifying multiple comma- or colon-separated languages triggers {ref}`g2p-cascade`. (required if input is plain text) |
| `-c, --config PATH`     | Use ReadAlong-Studio configuration file (in JSON format)                                                                                                |
| `--debug-g2p`           | Display verbose g2p debugging messages                                                                                                                  |
| `-s, --save-temps`      | Save intermediate stages of processing and temporary files (dictionary, FSG, tokenization, etc.)                                                        |
| `-f, --force-overwrite` | Force overwrite output files (handy if you’re troubleshooting and will be aligning repeatedly)                                                          |
| `-h, --help`            | Displays CLI guide for `align`                                                                                                                          |

See above for more information on the `-l, --language` argument.

A full command could be something like:

`readalongs align -f -c config.json story.readalong story.mp3 story-aligned`

**Is the text file plain text or XML?**

`readalongs align` accepts its text input as a plain text file or a ReadAlongs XML file.

- If the file name ends with `.txt`, it will be read as plain text.
- If the file name ends with `.xml` or `.readalong`, it will be read as ReadAlongs XML.
- With other extensions, the beginning of the file is examined to
  automatically determine if it's XML or plain text.

## Supported languages

The `readalongs langs` command can be used to list all supported languages.

Here is that list at the time of compiling this documentation:

```{eval-rst}
.. command-output:: readalongs langs
```

See {ref}`adding-a-lang` for references on adding new languages to that list.

## Adding titles, images and do-not-align segments via the config.json file

Some additional parameters can be specified via a config file: create
a JSON file called `config.json`, possibly in the same folder as
your other ReadAlong input files for convenience. The config file
currently accepts a few components: adding titles and headers, adding
images to your ReadAlongs, and DNA audio (see {ref}`dna`).

To add a title and headers to the output HTML, you can use the keys
`"title"`, `"header"`, and `"subheader"`, for example:

```
{
  "title": "My awesome read-along",
  "header": "A story in my language",
  "subheader": "Read by me"
}
```

To add images, indicate the page number as the key, and the name of the image
file as the value, as an entry in the `"images"` dictionary.

```
{ "images": { "0": "p1.jpg", "1": "p2.jpg" } }
```

Both images and DNA audio can be specified in the same config file, such
as in the example below:

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

Warning: mind your commas! The JSON format is very picky: commas
separate elements in a list or dictionnary, but if you accidentally have
a comma after the last element (e.g., by cutting and pasting whole
lines), you will get a syntax error.

(g2p-cascade)=

## The g2p cascade

Sometimes the g2p conversion of the input text will not succeed, for
various reasons. A word might use characters not recognized by the g2p mapping
for the language, or it might be in a different language. Whatever the
reason, the output for the g2p conversion will not be valid ARPABET, and
so the system will not be able to proceed to alignment by the
aligner, SoundSwallower.

If you know the language for that text, you can mark it as such in the
XML. E.g.:

```xml
<s xml:lang="eng">This sentence is in English.</s>
```

The `xml:lang` attribute can be added to any element in the XML structure
and will apply to text at any depth within that element, unless the
attribute is specified again at a deeper level, e.g.:

```xml
<s xml:lang="eng">English mixed with <foo xml:lang="fra">français</foo>.</s>
```

There is also a simpler option available: the g2p cascade. When the g2p
cascade is enabled, the g2p mapping will be done by first trying the
language specified by the `xml:lang` attribute in the XML file
(or with the first language provided to the `-l` flag on the
command line, if the input is plain text). For each word where the
result is not valid ARPABET, the g2p mapping will be attempted again
with each of the languages specified in the g2p cascade, in order, until
a valid ARPABET conversion is obtained. If no valid conversion is
possible, are error message is printed and alignment is not attempted.

To enable the g2p cascade, provide multiple languages via the `-l` switch
(for plain text input) or add the `fallback-langs="l2,l3,...` attribute to
any element in the XML file:

```xml
<s xml:lang="eng" fallback-langs="fra,und">English mixed with français.</s>
```

These command line examples will set the language to `fra`, with the g2p cascade
falling back to `eng` and then `und` (see below) when needed.

```bash
readalongs make-xml -l fra,eng myfile.txt myfile.readalong
readalongs align -l fra,eng myfile.txt myfile.wav output-dir
```

### The "Undetermined" language code: und

Notice how the sample XML snippet above has `und` as the last language in the
cascade. `und`, for Undetermined, is a special language mapping that
uses the definition of all characters in all alphabets that are part of the
Unicode standard, and
maps them as if the name of that character was how it is pronounced.
While crude, this mapping works surprisingly well for the purposes of
forced alignment, and allows `readalongs align` to successfully align
most text with a few foreign words without any manual intervention.

Since we recommend systematically using `und` at the end of the cascade, it
is now added by default after the languages specified with the `-l`
switch to both `readalongs align` and `readalongs make-xml`. Note that
adding other languages after `und` will have no effect, since the
Undetermined mapping will map any string to valid ARPABET.

In the unlikely event that you want to disable adding `und`, add the hidden
`--lang-no-append-und` switch, or delete `und` from the `fallback-langs`
attribute in your XML input.

### Debugging g2p mapping issues

The warning messages issued by `readalongs g2p` and `readalongs align`
indicate which words are causing g2p problems and what fallbacks were tried.
It can be worth inspecting to input text to fix any encoding or spelling
errors highlighted by these warnings. More detailed messages can be
produced by adding the `--debug-g2p` switch, to obtain a lot more
information about g2p'ing words in each language g2p was unsucessfully
attempted.

## Breaking up the pipeline

Some commands were added to the CLI in the last year to break processing up step
by step.

The following series of commands:

```
readalongs make-xml -l l1,l2 file.txt file.readalong
readalongs tokenize file.readalong file.tokenized.readalong
readalongs g2p file.tokenized.readalong file.g2p.readalong
readalongs align file.g2p.readalong file.wav output
```

is equivalent to the single command:

```
readalongs align -l l1,l2 file.txt file.wav output
```

except that when running the pipeline as four separate commands, you can
edit the XML files between each step to make manual adjustments and
corrections if you want, like inserting anchors, silences, changing the
language for indivual elements, or even manually editting the ARPABET encoding
for some words.

## Anchors: marking known alignment points

Long audio/text file pairs can sometimes be difficult to align
correctly, because the aligner might get lost part way through the
alignment process. Anchors can be used to tell the aligner about known
correspondance points between the text and the audio stream.

### Anchor syntax

Anchors are inserted in the XML file (the output of
`readalongs make-xml`, `readalongs tokenize` or `readalongs g2p`)
using the following syntax: `<anchor time="3.42s"/>` or
`<anchor time="3420ms"/>`. The time can be specified in seconds (this
is the default) or milliseconds.

Anchors can be placed anywhere in the XML file: between/before/after any
element or text.

Example:

```xml
<?xml version='1.0' encoding='utf-8'?>
<read-along version="1.0"> <text xml:lang="eng"> <body>
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
</body> </text> </read-along>
```

### Anchor semantics

When anchors are used, the alignment task is divided at each anchor,
creating a series of segments that are aligned independently from one
another. When alignment is performed, the aligner sees only the audio
and the text from the segment being processed, and the results are
joined together afterwards.

The beginning and end of files are implicit anchors: *n* anchors define
*n+1* segments: from the beginning of the audio and text to the first
anchor, between pairs of anchors, and from the last anchor to the end of
the audio and text.

Special cases equivalent to do-not-align audio:

- If an anchor occurs before the first word in the text, the audio up to that
  anchor’s timestamps is excluded from alignment.
- If an anchor occurs after the last word, the end of the audio is excluded
  from alignment.
- If two anchors occur one after the other, the time span between them in the
  audio is excluded from alignment.

Using anchors to define do-not-align audio segments is effectively the same as
marking them as "do-not-align" in the `config.json` file, except that DNA
segments declared using anchors have a known alignment with respect to the
text, while the position of DNA segments declared in the config file are
inferred by the aligner.

### Anchor use cases

1. Alignment fails because the stream is too long or too difficult to
   align.

   When alignment fails, listen to the audio stream and try to identify
   where some words you can pick up start or end. Even if you don’t
   understand the language, there might be some words you’re able to
   pick up and use as anchors to help the aligner.

2. You already know where some words/sentences/paragraphs start or end,
   because the data came with some partial alignment information. For
   example, the data might come from an ELAN file with sentence
   alignments.

   These known timestamps can be converted to anchors.

## Silences: inserting pause-like silences

There are times where you might want a read-along to pause at a particular
place for a specific time and resume again after. This can be accomplished by
inserting silences in your audio stream. You can do it manually by editing your
audio file ahead of time, but you can also have `readalongs align` insert the
silences for you.

### Silence syntax

Silences are inserted in the audio stream wherever a `silence` element is
found in the XML input.
**TODO say something about how the silence placement determined.**
The syntax is like the anchor syntax: `<silence dur="4.2s"/>` or
`<silence dur="100ms"/>`. Like anchors, silence elements can be inserted
anywhere.

Example:

```xml
<?xml version='1.0' encoding='utf-8'?>
<read-along version="1.0"> <text xml:lang="eng"> <body>
    <silence dur="1s"/>
    <div type="page">
    <p>
        <s>Hello.</s>
        <silence dur="10s"/>
        <s>After this pregnant pause, <silence dur="100ms"/> we'll pause
           again before it's all over!</s>
    </p>
    <silence dur="1s"/>
    </div>
</body> </text> </read-along>
```

### Silence use cases

1. Your read along has a title page that is not read out in the audio stream:
   insert a silence at the beginning so that it stays on the first page for
   the specified time.
   **TODO: test that a silence before the first word really keeps the RA on the
   first page during that silence, even if all text on the first page is DNA.**
2. Your read along has a credits page at the end that is not read out in the
   audio stream: insert a silence at the end so that people see that credits
   page for the specified time before the streaming end.
   **TODO: also test that this use case works as described.**
