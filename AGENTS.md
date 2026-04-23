# AGENTS.md

This repository contains the package distribution for the
GAP computer algebra system.

## AI disclosure

Any use of AI tools for preparing code, documentation, tests, commit messages,
pull requests, issue comments, or reviews for this repository must be
disclosed. Include a brief note saying which AI tool was used and what kind of
assistance it provided. Add the AI tool as a Git co-author on all commits
created by that tool (e.g. via an `Co-authored-by: ` line).

## Repository layout

- `README.md`: top-level package overview.
- `packages` contains one subdirectory per GAP package, each with a
  `meta.json` file describing the package version, URLs, checksums, test
  configuration, and related metadata used by the distribution workflows
- `tools` contains the Python and GAP helper scripts that download archives,
  validate package metadata, assemble release artifacts, generate reports, and
  support the Python test suite in `tools/tests`
- `.github` contains the GitHub Actions workflows that validate package
  metadata, run package tests, assemble release artifacts, and check the
  Python tooling in `tools/`

Additionally, several directories are not in the repository but are
used by some of the tools for various purposes:

- `_archives` is used to store copies of all package archives
- `_pkginfos` stores copies of the `PackageInfo.g` files
- `_releases` stores generated release artifacts such as `packages.tar.gz`,
  `packages-required.tar.gz`, `package-infos.json.gz`, checksums, and package
  lists created by `tools/assemble_distro.py`

## Python tooling

The Python scripts in `tools/` are formatted with `black`. Keep Python code
formatted with `python -m black tools`.

The CI workflow in `.github/workflows/tools-tests.yml` currently runs these
checks for Python changes:

- `python -m black --check --diff tools`
- `python -m isort --check --profile black tools`
- `python -m mypy --disallow-untyped-calls --disallow-untyped-defs tools/*.py`
- `python -m pytest tools/tests/test*.py -vv`

Before finishing changes to Python code in `tools/`, run the relevant subset
of those commands locally. If you touch multiple scripts or shared helpers,
run all of them.

## Commit messages and pull requests

When writing commit messages, use the title format `component: Brief summary`
The title line should not exceed 60 characters.

In the body, give a brief prose summary of the purpose of the change. Do not
specifically call out added tests, comments, documentation, and similar
supporting edits unless that is the main purpose of the change. Do not include
the test plan unless it differs from the instructions in this file. If the
change fixes one or more issues, add `Fixes #...` at the end of the commit
message body, not in the title.

Don't write lines into the commit message that are wider than 70 characters.

Pull requests should follow the same style: a short summary up top, concise
prose describing the change, issue references when applicable, and an explicit
AI-disclosure note if AI tools were used.
