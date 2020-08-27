# Contributing to ReadAlong Studio

This file is just starting to be written, and is work in progress.
The intent is to document how to get going with our commit hooks and other conventions.
Please add to this or fix any errors!

## Enabling pre-commit

The ReadAlong Studio team has agreed to systematically use a number of pre-commit hooks to
normalize formatting of code. You need to install and enable pre-commit to have these used
when you do your own commits.

```sh
pip install pre-commit
pre-commit install
```

Pre-commit hooks enabled:
- Black: non-compromising formatting of Python code
- Flake8: mode in-depth validation of Python code

## Enabling husky and commitlint

We've already agreed to use commitlint-style commit messages. Install and enable
[commitlint](https://github.com/conventional-changelog/commitlint) to have your commits
validated systematically.

- If you don't already use node or nvm, install nvm in your ~/.nvm folder:
```sh
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.3/install.sh | bash`
```

- Install node, preferably version 12.18.3
```sh
nvm install node && nvm install 12.18.3
```

- Use node 12.18.3: you need to do this each time, so adding it to your .bashrc is a good
  idea unless you already use other version sof nodes for other projects
```sh
nvm use 12.18.3
```

- In your ReadAlong/Studio sandbox, install the husky commit-msg hook using npm, the node
  package manager you just installed using nvm. The file `package.json` in Studio is what
  tells npm to install husky as a pre-commit hook, and also what tells husky to invoke
  commitlint on your commit messages.
```sh
npm install
```

- Now, next time you make a change and commit it, your commit log will be checked:
  - `git commit -m'non-compliant commit log text'` outputs an error
  - `git commit -m'fix(g2p): fixing bug in g2p module'` works
