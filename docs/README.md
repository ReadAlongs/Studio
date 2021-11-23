# Contributing to the documentation

## Edit the files

To contribute to the ReadAlongs Studio documentation, edit the `.rst` files in
this folder.

## Build the documentation locally

To build the documention for local inspection, run one of these commands,
which will build the documentation in `./_build/html/` or
`./_build/singlehtml/`:

    make html  # multi-page HTML site
    make singlehtml  # single-page HTML document

## View the documentation locally

To view the documentation, run an HTTP server in the directory where the build
is found, e.g.,

    cd _build/html
    python3 -m http.server

and navigate to http://127.0.0.1:8000 to view the results (or whatever port
your local web server displays).

## Publish the changes

Once your changes are pushed to GitHub and merged into `master` via a Pull
Request, the documentation will be automatically built and published to
https://readalong-studio.readthedocs.io/en/latest/
