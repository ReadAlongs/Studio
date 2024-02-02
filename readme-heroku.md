Our production Heroku deployment is controlled by the following files:
 - `Procfile`: tells Heroku what command to launch in each Dyno;
 - `runtime.txt`: tells Heroku which run-time engine to use (i.e., which version of Python);

   Heroku detects Python by default, but `runtime.txt` lets us specify/bump the version as needed;
 - `requirements.txt`: tells Heroku what our production dependencies are.

Updating `g2p`:
 - By default, `g2p` only gets updated for `readalong-studio` on Heroku when:
   - we make a new release of `g2p` on PyPI
   - we update `requirements.min.txt` here to ask for that release
 - Manual override: it is also possible to update g2p to the current commit on the `main` branch using this procedure:
   - Change `requirements.min.txt` to specify `g2p @ git+https://github.com/roedoejet/g2p@main`.
   - Commit that change to `main` in a sandbox connected to Heroku.
   - `git push heroku main`
   - This will force a build which will fetch the main branch of g2p from GitHub.
   - Subsequent builds reuse the cached g2p, so they'll reuse this one. Exception: if `runtime.txt` is updated, a fresh build is done and g2p will be reverted to the latest published version.
