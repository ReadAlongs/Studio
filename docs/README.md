# Contributing to the documentation

## Edit the files

To contribute to the ReadAlongs Studio documentation, edit the `.rst` files in
this folder.

## Build and view the documentation locally

To build the documentation and review your own changes locally:

1. Install the required build software, Sphinx:

       pip install -r requirements.txt

2. Run one of these commands, which will build the documentation in `./_build/html/`
   or `./_build/singlehtml/`:

       make html  # multi-page HTML site
       make singlehtml  # single-page HTML document

3. View the documentation by running an HTTP server in the directory where the
   build is found, e.g.,

       cd _build/html
       python3 -m http.server

   and navigating to http://127.0.0.1:8000 (or whatever port your local web
   server displays).

## Publish the changes

Once your changes are pushed to GitHub and merged into `master` via a Pull
Request, the documentation will automatically get built and published to
https://readalong-studio.readthedocs.io/en/latest/
