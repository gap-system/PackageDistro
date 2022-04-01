# PackageDistro

The GAP package distribution is managed via this repository: this repository
contains the metadata of all the GAP packages in the distribution. We also
upload snapshots the package distribution tarballs to appropriate release tags
on this repository.

## High-level status dashboard

| Test            | GAP `master` | GAP `4.11.1` |
|:---------------:|:----------:|:----------:|
| Released packages | [![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/gap-system/PackageDistro/data/badges/latest-master/badge.json)](https://gap-system.github.io/PackageDistro/latest-master/redirect.html) | [![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/gap-system/PackageDistro/data/badges/latest-4.11.1/badge.json)](https://gap-system.github.io/PackageDistro/latest-4.11.1/redirect.html) |

## Metadata

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



## Workflows

All of this is driven by several GitHub Workflows  which automate most of the
maintenance on the GAP package distribution. For details on how they operate,
have a look at the `.yml` files in `.github/workflows`.

These workflows are in parts implemented by calling scripts in the `tools` directory.


## Scripts

The scripts in the `tools` directory are written in Python 3 or GAP. For the Python
scripts, you must make sure their prerequisites are installed, e.g. by invoking the
following command once from the root of this repository:

    python -m pip install -r tools/requirements.txt

For information about what each script does, please consult its source,
which should have comments explaining what it does and how to invoke it.


## Other directories

The various scripts use a bunch of auxiliary directories to store and exchange data:

- `_archives` is used to store copies of all package archives
- `_pkginfos` stores copies of the `PackageInfo.g` 
- `_releases`
- `_unpacked_archives`
