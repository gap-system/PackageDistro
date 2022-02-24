# PackageDistroTools

This repository contains tools for maintaining the
[GAP package distribution](https://github.com/gap-system/PackageDistro).

Below we give an overview of the available scripts and the various GitHub
Workflows.

## The scripts

The following scrips are provided. The usage examples assume that we start in
a git clone of the `PackageDistro`  repository, and that a clone of of
`PackageDistroTools` exists in the `_tools` subdirectory

Some of the scripts store package tarballs in the directory `_archive` inside
the package distribution directory. This directory is not part of the
distribution repository (in fact it is listed in `.gitignore`). It exists to
help us avoid re-downloading package tarballs again and again. For the Github
Workflows, these files are stored in a cache and thus persist across CI jobs.

Some of the scripts store `PackageInfo.g` files in the directory `_pkginfos` inside
the package distribution directory.


### `scan-for-updates.py`

Iterates over all metadata files in the package distribution, and do the following:

- extract the `PackageInfoURL` and `PackageInfoSHA256` fields from the
  metadata
- download the `PackageInfo.g` file from the URL, store it as `_pkginfos/package_name.g`, - iterate over all of these `PackageInfo.g` files. parse them with GAP, and output
  the result into the corresponding `meta.json` files

Usage:

    cd PackageDistro
    _tools/scan-for-updates.py


### `validate-package.py`

Takes one (or multiple?) PackageInfo.g file (path) as argument, then...
  - validates it using `ValidatePackageInfo()` 
  - reject `DEV` package versions
  - reject versions (and release dates?) that come before the package info currently in store for that package (if any)
  - possibly do further validation (e.g. validate `README_URL`???)
  - downloads one of the associated archives (and perhaps extracts its `PackageInfo.g`, and verifies it has a matchin checksum?)
    - if possible we want .tar.gz; in case any package doesn't have one, we may need a script to generate one (e.g. tar.bz2 is trivial, not sure if there is a package that only offers .zip? perhaps we should *require* a `.tar.gz`???)
  - computes checksums of PI.g and the archive, adds them to the metadata
  - writes out the metadata as JSON
- alternate usecase: take the name of a .tar.gz as argument;
  extract its `PackageInfo.g`, then proceed similar to before?!?


### `upload-package.py`

- to upload such a package tarball to GitHub release (could use [GitHub's `gh` tool](http://cli.github.com) or adapt the code)
- also would be nice to be able to upload to our own server, but that'll probably amount to a `scp FILE.tar.gz ourserver:/some/path` done in a GH action, which gets a suitable SSH prviate key (granting it write access) via a repository secreet


### `assemble-distro.py`

- scans over all metadata, collects the appropriate tarballs, then "merges" them into one big tarball
- the assembled distro archive also needs to be uploaded, but ideally we can just repurpose `upload-package.py`
- should do caching: download tarballs into a specific fixed location; if a file with the right name already exists and has the right checksum, just use it


## Automation using GitHub Actions

The scripts from the previous section are called from GitHub Workflows on the
`PackageDistro` repository to automate most of the maintenance on the GAP
package distribution.

These workflows typically clone the `PackageDistroTools` repository into a
directory named `_tools` inside the `PackageDistro` clone.

The following jobs exist (for further details, look at their sources in
<https://github.com/gap-system/PackageDistro/tree/main/.github/workflows>.


### Cron job on `PackageDistro`

A GH action that runs regulalry and updates PRs for package updates,
one per package (if someone needs to update multiple packages in one
PR, they have to submit a PR manually)

- This CI job is called regularly, e.g. once per hour or day or so
- It invokes the `scan-for-updates.py` script
- it then loops over the reported `PackageInfo.g` files, and for each...
  - check if an update branch already exists, say `update/pkgname`
     - if it does, check it out
        - if the metadata differs, then update the branch and force push it
        - check if a PR is still open for that branch; if not, open one        
          (this deals with the case when a PR is accidentally removed/close/not created
           due to a hiccup before. Note that this means: if maintainers don't want a
           certain package release for whatever reason: don't close that PR, leave
           it open (possibly marked with a label)
     - if no such branch exists
        - create a new branch
        - update it with the new metadata
        - push it
        - open a new PR

TODO TODO TODO: actually there is a mismatch here between what this CI job is
supposed to do and what the `import-package.py` script does. Seems we need to
parse the `PackageInfo.g` files in here as well, to "update the JSON"


## CI job for pull requests on  `PackageDistro`

- this is run on all PRs
- detects which packages are added / modified / removed in the PR
- for removed packages:
  check that no other package has a dependency on that package!
  error if there is one
- for added / modified packages:
   - run `import-package.py` in GH Action stept
   - once that step has successfully completed, launch a number of test jobs
     testing things in various combinations (different GAP versions, architectures, etc.):
     - compile the package if necessary
     - run the CI tests of the new package with all/default/minimal package set
       - in particular we test: does `LoadAllPackages()` still work?
     - ideally: also run CI tests of all other packages with the new package loaded...
       but that's expensive (and closely related to what we do in the `gap-infra` CI)
   - ...

- if all tests pass, AND the PR was created by our automation, we can merge it
  automatically
- for PRs that pass but are not by our automation, a human must merge them -- to
  make sure that happens, perhaps the issue can notify them (e.g. by commenting on
  the PR: "Hi @gap-system/TEAM-NAME-TO-BE-SET-UP, this PR is ready and needs a review")
- if the PR fails, ideally notify the package maintainers (if we knew their GitHub usernames, we could also do this via a PR comment, @-mentioning them... see also <https://github.com/gap-system/gap/issues/4784>)


## CI job for push to `main` on `PackageDistro`

- this run when master is updated
- invokes `assemble-distro.py`
- ...



## The format of the package distribution

TODO: discuss the file layout

TODO: discuss the JSON format


