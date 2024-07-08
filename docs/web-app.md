# ReadAlong Studio Web Applications

## The ReadAlong Studio Web App

The ReadAlong Studio functionality can now be used both from a CLI (see the rest of this guide) and a web application meant to be as easy to use as possible.

See

 - [ReadAlongs-Studio Web App](https://readalong-studio.mothertongues.org/),
 - [El Studio de ReadAlong en español](https://readalong-studio.mothertongues.org/es/), or
 - [L'appli Studio ReadAlong en français](https://readalong-studio.mothertongues.org/fr/).

The usage documentation for the web app can be access by clicking on "Take the tour"/"¡Siga el tour!"/"Visite guidée" button at the top of the page. We encourage you to take this tour on your first visit, or if you have not taken it yet, as it explains all the parts of the process.

### Web app features

The web app supports the most commonly used features of the ReadAlong Studio:

 - recording audio or using pre-existing audio
 - typing text or using pre-existing text
 - creating the readalongs
 - adding translations
 - adding images
 - saving the results in the single file Offline HTML format
 - saving the results in a multi-file Web Bundle for [deployment on a web page](outputs.md#simple-web-deployment)

### Input text format

The input text has to be provided in the same format as for the CLI. As documented by clicking on `? Format` in the Text input box:

 - Each line should ideally contain one sentence, although that is not a strict rule.
 - Paragraph breaks are indicated by inserting a blank line.
 - Page breaks are indicated by inserting two consecutive blank lines.

## The ReadAlong Studio Editor

Recently, the team has also added a much requested feature: the Editor, where you can improve the alignments or fix errors in your readalong.

Links:

 - [ReadAlong Studio Editor](https://readalong-studio.mothertongues.org/#/editor)
 - [L'éditeur du Studio ReadAlong](https://readalong-studio.mothertongues.org/fr/#/editor)
 - [El editor del Studio de ReadAlong](https://readalong-studio.mothertongues.org/es/#/editor)

### Opening a ReadAlong in the Editor

The Editor can only read the single file Offline HTML format produced by the ReadAlongs Studio.

You can get this file in various ways:

 - By downloading the Offline HTML file format from the ReadAlongs Studio Web App (this is the default format).
 - If you downloaded a Web Bundle, you will find an Offline-HTML folder in the zip file containing it.
 - From the CLI, using the `-o html` option to `readalongs align` generates the Offline HTML file.

### Editor features

In the Editor, you can:

 - Fix alignment errors made by the automatic alignment, by dragging word boundaries in the Audio Toolbar at the bottom.
 - Fix spelling mistakes in your text, by modifying words in the Audio Toolbar at the bottom.
 - Add/remove/update images and translations in your readalong.
 - Update your title and subtitle.
 - Convert your Offline HTML file into the Web Bundle and other export formats.
