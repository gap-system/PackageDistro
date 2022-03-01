#!/usr/bin/env python3

#############################################################################
##
##  This file is part of GAP, a system for computational discrete algebra.
##
##  Copyright of GAP belongs to its developers, whose names are too numerous
##  to list here. Please refer to the COPYRIGHT file for details.
##
##  SPDX-License-Identifier: GPL-2.0-or-later
##

# pylint: disable=C0116, C0103

"""
This module can be used as a script to download package archives into the
`_archives` directory of the cwd. The command should be run inside the
`PackageDistro` git repo from:

https://github.com/gap-system/PackageDistro

The packages to download should be given as command line arguments, each
given name must either correspond to a subdirectory in the cwd named
`pkg_name` and containing a `meta.json` file, or be of the form
`pkg_name/meta.json`.

If the archive already exists in the `_archives` directory, then it is not
downloaded again.

Usage:

    > _tools/download_packages.py digraphs walrus/meta.json
    digraphs: _archives/digraphs-1.5.0.tar.gz already exists, not downloading again
    walrus: _archives/walrus-0.9991.tar.gz already exists, not downloading again

"""


import json
import os
import sys
from os.path import join

import requests
from accepts import accepts

from utils import error, notice


@accepts(str)
def metadata(pkg_name: str) -> dict:
    fname = join(pkg_name, "meta.json")
    pkg_json = {}

    try:
        with open(fname, "r", encoding="utf-8") as f:
            pkg_json = json.load(f)
    except (OSError, IOError):
        error("{}: file {} not found".format(pkg_name, fname))
    except json.JSONDecodeError as e:
        error("{}: invalid json in {}\n{}".format(pkg_name, fname, e.msg))
    return pkg_json


@accepts(str)
def archive_name(pkg_name: str) -> str:
    pkg_json = metadata(pkg_name)
    return (
        pkg_json["ArchiveURL"].split("/")[-1]
        + pkg_json["ArchiveFormats"].split(" ")[0]
    )


@accepts(str)
def archive_url(pkg_name: str) -> str:
    pkg_json = metadata(pkg_name)
    return pkg_json["ArchiveURL"] + pkg_json["ArchiveFormats"].split(" ")[0]


@accepts(str, str, int)
def download_archive(  # pylint: disable=inconsistent-return-statements
    archive_dir: str, pkg_name: str, tries=5
) -> str:
    """Returns the full archive name (including archive_dir) for the downloaded
    archive of the package `pkg_name`"""
    if not os.path.exists(archive_dir):
        os.mkdir(archive_dir)

    archive_fname = join(archive_dir, archive_name(pkg_name))
    archive_ext = archive_fname.split(".")
    if archive_ext[-1] == "gz" or archive_ext[-1] == "bz2":
        archive_ext = "." + ".".join(archive_ext[-2:])
    else:
        assert archive_ext[-1] == "zip"
        archive_ext = ".zip"

    if os.path.exists(archive_fname) and os.path.isfile(archive_fname):
        notice(
            "{}: {} already exists, not downloading again".format(
                pkg_name, archive_fname
            )
        )
        return archive_fname
    url = archive_url(pkg_name)
    notice("{}: downloaded {} to {}".format(pkg_name, url, archive_fname))

    for i in range(tries):
        try:
            response = requests.get(url, stream=True)
            with open(archive_fname, "wb") as f:
                for chunk in response.raw.stream(1024, decode_content=False):
                    if chunk:
                        f.write(chunk)
            return archive_fname
        except requests.RequestException:
            notice("{}: attempt {}/{} failed".format(pkg_name, i + 1, tries))

    error("{}: failed to download archive".format(pkg_name))


def main(pkg_names) -> None:
    archive_dir = "_archives"
    for pkg_name in pkg_names:
        download_archive(archive_dir, pkg_name.removesuffix("/meta.json"))


if __name__ == "__main__":
    main(sys.argv[1:])
