# Contributing to the documentation

## Edit the files

To contribute to the ReadAlongs Studio documentation, edit the `.md` files in
this folder.

The configuration is found in `../mkdocs.yml`.

## Build and view the documentation locally

To build the documentation and review your own changes locally:

1. Install the required build software, mkdocs and friends:

    pip install -r requirements.txt

2. Install Studio itself

    (cd .. && pip install -e .)

3. Run this command to serve the documentation locally:

    (cd .. && mkdocs serve)

4. View the documentation by browing to <http://localhost:8000>.

## Publish the changes

Once your changes are pushed to GitHub and merged into `main` via a Pull
Request, the documentation will automatically get built and published to
<https://readalong-studio.readthedocs.io/en/latest/>
