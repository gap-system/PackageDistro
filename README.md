# The GAP package distribution

The GAP package distribution is managed via this repository: specifically, it
contains the metadata of all the GAP packages in the distribution. We also
upload snapshots of the package distribution to appropriate release tags
on this repository.

## High-level status dashboard

| Test            | GAP `master` | GAP `4.13.1` |
|:---------------:|:----------:|:----------:|
| Released packages | [![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/gap-system/PackageDistro/data/badges/latest-master/badge.json)](https://gap-system.github.io/PackageDistro/latest-master/redirect.html) | [![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/gap-system/PackageDistro/data/badges/latest-4.13.1/badge.json)](https://gap-system.github.io/PackageDistro/latest-4.13.1/redirect.html) |

## Instructions for package authors

### How to submit package updates

We automatically detect package updates provided these rules are followed:
1. The `PackageInfoURL` in the `PackageInfo.g` file of the current version of
   your package in the package distribution is valid and points to a copy of
   that file from the new version of your package.
2. In this `PackageInfo.g` file, the `ArchiveURL` is valid (i.e. when one adds
   a file extension from `ArchiveFormats` it points to an archive containing
   your package).

We scan the `PackageInfoURL` for all packages in the distribution once every hour for updates. When a new
version is detected this way, the package is downloaded and a new pull request
for the update is opened on this repository. A bunch of CI tests are then
started. Assuming they pass, a human will merge that PR, which means your
update is accepted. If a problem is detected, we will instead contact you to
discuss how to resolve it.

In the event that your package is to be moved to a new website, there are two ways
to go about this that ensure we will still be able to pick up updates:
1. If you still have access to the old location, simply upload the new `PackageInfo.g`
   file (containing the new URLs and of course also a new version number) in both
   the old and the new location. The system then will as usually automatically detect it,
   and once the update is accepted and merged, the system
   will use only the new `PackageInfoURL`.
2. If this is not possible, you can also submit the update as if it was a new package,
   using one of the options listed in the next section.

### How to submit a new package

There are several options how to do this.

1. (**RECOMMENDED**) Submit an issue to this repository, requesting that your package be added.
   Make sure to include a link to the `PackageInfo.g` file of your package.
   Note that such requests are visible to the anyone watching this repository.

2. Send an email to <support@gap-system.org>, requesting that your package be added.
   Make sure to include a link to the `PackageInfo.g` file of your package.
   Note that such requests are visible to only to a small group of people listed
   [on this web page](https://www.gap-system.org/Contacts/People/supportgroup.html).

In either case, we will evaluate your request and will inform you about the
outcome of that (which may be: accept, accept after modifications, reject).


## Instructions for maintainers of the package distribution

### Adding a new package

_**WARNING:** The following instructions are only about the technical aspects
of adding a new package. In general we may also want to impose other requirements
for adding new packages to the distribution._

People who have write access to this repository should add new packages by
creating a pull request for each new package. One way to do that is manually,
as described above. Alternatively, this can be achieved via a GitHub workflow
as follows:

1. Go to <https://github.com/gap-system/PackageDistro/actions/workflows/scan-for-updates.yml>
2. Click "Run workflow" once to open a popup menu. There is a field there accepting
   a space separated list of `PackageInfo.g` URLs. Do so.
3. Click on the new green "Run workflow" button to actually trigger the workflow.
4. After 2-3 minutes this should create a new pull request for each package you listed.

Once the PR is created, a bunch of CI tests are started. Once they are completed,
a report is added to the PR which indicates whether the new package breaks something
in GAP or other packages, and whether its tests pass. If all looks good, the
PR may be merged by any maintainer.


## How everything works

The following is an overview of the internals of how everything works.

### Metadata

For each package in the GAP package distribution, there is a subdirectory of
the `packages` directory whose name equals that of the package with all
letters turned to lower case. In that directory is a file called `meta.json`
which contains the metadata for that package as [JSON](https://json.org).

For example, the metadata of ACE package is contained in `packages/ace/meta.json`.

The content of the `meta.json` file for package is obtained by reading its
`PackageInfo.g` file in a GAP script, then turning this into JSON data where
possible (basically integers, strings, lists and records are converted to
their natural JSON counterparts; but e.g. functions are obviously not
convertible this way and thus are simply ignored). This is basically the same
form as used by the GAP release scripts to encode which packages are bundled
with a GAP release, except that there it is one big file, while here we have
one file per packages.

In addition to this, we also store the SHA256 checksum of the `PackageInfo.g`
file resp. of the first package archive under the keys `PackageInfoSHA256` resp.
`ArchiveSHA256`. Here, with "the first package archive", we mean that we
take the archive with first format extension specified by the `ArchiveFormats` field of
the package info record.

For example, the SHA256 in this excerpt of a `meta.json` file refers to the
`.tar.gz` file

    "ArchiveFormats": ".tar.gz .zip",
    "ArchiveSHA256": "15c516d89863916ef8f4b0d5c68f5b79cb41b75741fc3b604a6a868569dcda38",
    "ArchiveURL": "https://github.com/homalg-project/ToricVarieties_project/releases/download/2022-03-04/ToricVarieties",


### GitHub Workflows

All of this is driven by several [GitHub Workflows](https://docs.github.com/en/actions)
which automate most of the maintenance on the GAP package distribution. For
details on how they operate, have a look at the `.yml` files in
`.github/workflows`.

These workflows are in parts implemented by calling scripts in the `tools` directory.


## Requirements

The scripts in the `tools` directory are written in Python 3 or GAP. For the Python
scripts, you must make sure their prerequisites are installed, e.g. by invoking the
following command once from the root of this repository:

    python -m pip install -r tools/requirements.txt

For information about what each script does, please consult its source, which
should have comments explaining what it does and how to invoke it.

If you need to make changes to the Python code, note that we are using the
[`black`](https://github.com/psf/black) code formatter. Pull requests modifying
or adding Python code must run `black` on all Python files in order to pass the
test suite and be merged.


## Other directories

The various scripts create and/oruse a bunch of auxiliary directories to store
and exchange data:

- `_archives` is used to store copies of all package archives
- `_pkginfos` stores copies of the `PackageInfo.g` 
- `_releases`: TODO
- `_unpacked_archives`: TODO


## What do we test, and how?

In a nutshell, when a new package update is received, we validates its
metadata (including validating URLs in it), and run the testsuites of GAP and
of all GAP packages in the package distribution. If any of these detects an
issue, this is reported.

Some more details:
- if a package update is detected, we fetch its latest metadata and validate it
  - This can be replicated manually by doing the following in an up-to-date clone
    of the PackageDistro repository (substitute `example` by the name of your package)
    ```
    ./tools/scan_for_updates.py example
    ./tools/validate_package.py example
    ```
    However this only works if you already made a release, as it downloads the metadata
    from the `PackageInfoURL` (see also <https://github.com/gap-system/PackageDistro/issues/1024>).
  - The checks this perform include
      - check output of GAP function `ValidatePackageInfo`
      - verify version is greater than previous version and does not contain `dev`
      - verify release date is not less than previous release date
      - verify release date is not in the future
      - verify URLs are valid (currently `PackageInfoURL`, `README_URL`, source archives)
      - validates source archives, including:
        - must not contain absolute paths, or rather: all files in the archive must be
          contained in a single parent subdirectory
        - must contain `PackageInfo.g`
        - must not contain symlinks
- clone the GAP repository and build GAP
  - this (and all steps after this) is actually done twice, once for the latest
    GAP `master` branch and once for the latest `stable-X.Y` branch)
- compile all packages that require it
  - actually we skip `xgap` and also don't test it for technical reasons
- start GAP, execute `LoadAllPackages()`, run GAP's `testinstall` test suite
- for each package `pkgname` in the distribution
  - start GAP, do `LoadPackage("pkgname")` then `TestPackage("pkgname")`
  - start GAP, do `LoadPackage("pkgname" : OnlyNeeded)` then `TestPackage("pkgname")`
    - unfortunately quite some packages have issues with that as their test
    suites actually require more than the minimal set of dependencies. We
    currently are lenient there and include custom treatment for a bunch of
    packages (for details see the "Run tests with OnlyNeeded" step in
    `.github/workflows/test-all.yml`)
