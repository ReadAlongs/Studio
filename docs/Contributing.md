# Contributing to the documentation

## Edit the files

To contribute to the ReadAlongs Studio documentation, edit the `.md` files in
this folder.

The configuration is found in `../mkdocs.yml`.

## Build and view the documentation locally

To build the documentation and review your own changes locally, runs these
commands at the root of your Studio sandbox:

1. Install Studio and the required build software (mkdocs and friends):

       pip install -e '.[docs]'

2. Run this command to serve the documentation locally:

       mkdocs serve

3. View the documentation by browing to <http://localhost:8000>.
The page will auto update as you edit the documentation `.md` files.

## Publish the changes

Once your changes are pushed to GitHub and merged into `main` via a Pull
Request, the documentation will automatically get built and published to
<https://readalongs.github.io/Studio/latest/>.
