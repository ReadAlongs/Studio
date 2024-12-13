Our production Heroku deployment is controlled by the following files:
 - `Procfile`: tells Heroku what command to launch in each Dyno;
 - `runtime.txt`: tells Heroku which run-time engine to use (i.e., which version of Python);
 - `requirements.txt`: tells Heroku what our production dependencies are;
 - `bin/post_compile`: Heroku builds run this after doing `pip install -r requirements.txt`.

Updating dependencies:
 - Our dependencies are declared in `pyproject.toml`. This is where changes should be made first.
 - `requirements.txt` is the generated "lock" file that Heroku uses. To update it,
   run these commands, preferably from a Linux machine to match the Heroku context:

       hatch env remove prod
       rm requirements.txt
       hatch env create prod

   It is also possible to edit it manually, e.g., to handle a critical vulnerability report,
   but an occasional full rebuild is a good idea, to keep things up to date.

Updating `g2p`:
 - By default, `g2p` only gets updated for `readalong-studio` on Heroku when:
   - we make a new release of `g2p` on PyPI, **and**
   - we update `requirements.txt` here to ask for that release
 - Manual override: it is also possible to update g2p to the current commit on the `main` branch using this procedure:
   - Change `requirements.txt` to specify `g2p @ git+https://github.com/roedoejet/g2p@main`.
   - Commit that change to `main` in a sandbox connected to Heroku.
   - `git push heroku main`
   - This will force a build which will fetch the main branch of g2p from GitHub.
   - Subsequent builds reuse the cached g2p, so they'll reuse this one. Exception: if `runtime.txt` is updated, a fresh build is done and g2p will be reverted to the latest published version.
