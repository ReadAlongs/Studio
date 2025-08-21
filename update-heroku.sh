#!/bin/bash
# Refresh the production environment for Heroku, i.e., update requirements.txt

if [[ $(uname) != Linux ]]; then
    echo Please run this command on Linux
    exit 1
fi

if ! which uvx > /dev/null; then
    echo Please install uv: "https://docs.astral.sh/uv/getting-started/installation/"
    echo "Simplest: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "Removing old prod env"
uvx --with hatch-pip-compile hatch env remove prod
rm requirements.txt
echo "Creating new prod env -- errors about pip's dependency resolver are expected and normal"
uvx --with hatch-pip-compile hatch env create prod

echo "Applying manual overrides"
sed -i -e '/^soundswallower=/i # Manual override: soundswallower is not needed for the web API so ignore it.' \
       -e 's/^soundswallower=/# soundswallower=/' requirements.txt

sed -i -e '/^g2p=/i # Manual override: for deployment on Heroku, we want the latest g2p@main on GitHub' \
       -e '/^g2p=/i g2p @ git+https://github.com/roedoejet/g2p.git@main' \
       -e 's/^g2p=/# g2p=/' \
       requirements.txt

echo "Please review the changes to requirements.txt and commit them if they're OK."
