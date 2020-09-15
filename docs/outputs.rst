.. outputs:

Output Realizations
===================

One of the main motivations for ReadAlong-Studio was to provide a one-stop-shop for audio/text alignment.
With that in mind, there are a variety of different output formats that can be created. Here are a few:

Elan/Praat files
----------------

Web Component
-------------

When you have standard output from ReadAlong-Studio, consisting of 1) a text file (XML) 2) an audio file and 3) an alignment file (SMIL)
you can mobilize these files to the web or hybrid mobile apps quickly and painlessly.

This is done using the ReadAlong WebComponent. Web components are re-useable, custom-defined HTML elements that you can embed in any HTML, regardless of which
framework you used to build your site, whether React, Angular, Vue, or just Vanilla HTML/CSS/JS.

Below is an example of a minimal implementation in a basic standalone html page. Please visit https://stenciljs.com/docs/overview for more information on framework integrations.

.. code-block:: html

    <!DOCTYPE html>
    <html>

        <head>
            <!-- Import fonts. Material Icons are needed by the web component -->
            <link href="https://fonts.googleapis.com/css?family=Lato|Material+Icons|Material+Icons+Outlined" rel="stylesheet">
        </head>

        <body>
            <!-- Here is how you declare the Web Component -->
            <read-along text="assets/sample.xml" alignment="assets/sample.smil" audio="assets/sample.wav"></read-along>
        </body>
        <!-- The last step needed is to import the package -->
       <script type="module" src='https://unpkg.com/@roedoejet/readalong@latest/dist/read-along/read-along.esm.js'></script>
       <script nomodule src='https://unpkg.com/@roedoejet/readalong@latest/dist/read-along/read-along.js'></script>
    </html>


The above assumes the following structure:

| web
| ├── assets
| │   ├── sample.smil
| │   ├── sample.wav
| │   ├── sample.xml
| ├── index.html
|
|

Then you can host your site anywhere, or run it locally (``cd web && python3 -m http.server`` for example)
