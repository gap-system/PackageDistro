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

    > tools/download_packages.py digraphs walrus/meta.json
    digraphs: _archives/digraphs-1.5.0.tar.gz already exists, not downloading again
    walrus: _archives/walrus-0.9991.tar.gz already exists, not downloading again

"""


import os
import sys
from os.path import join

from typing import List

import requests

from utils import (
    error,
    notice,
    normalize_pkg_name,
    archive_name,
    archive_url,
    metadata,
    sha256,
)


def download_archive(  # pylint: disable=inconsistent-return-statements
    archive_dir: str, pkg_name: str, tries: int = 5
) -> str:
    """Returns the full archive name (including archive_dir) for the downloaded
    archive of the package `pkg_name`"""
    if not os.path.exists(archive_dir):
        os.mkdir(archive_dir)

    pkg_json = metadata(pkg_name)
    archive_fname = join(archive_dir, archive_name(pkg_name))

    if os.path.exists(archive_fname) and os.path.isfile(archive_fname):
        archive_sha = sha256(archive_fname)
        if "ArchiveSHA256" in pkg_json and pkg_json["ArchiveSHA256"] != archive_sha:
            notice(
                f'{archive_fname} has SHA256 {archive_sha}, expected {pkg_json["ArchiveSHA256"]}'
            )
            os.remove(archive_fname)
        else:
            notice(f"{archive_fname} already exists, not downloading again")
            return archive_fname
    url = archive_url(pkg_json)
    notice(f"downloading {url} to {archive_fname}")

    for i in range(tries):
        try:
            response = requests.get(url, stream=True)
            if response.status_code != 200:
                notice(f"exited with HTTP status {response.status_code}")
                break
            with open(archive_fname, "wb") as f:
                for chunk in response.raw.stream(1024, decode_content=False):
                    if chunk:
                        f.write(chunk)
            return archive_fname
        except requests.RequestException:
            notice(f"  attempt {i+1}/{tries} failed")

    error(f"  failed to download archive {archive_fname}")


def main(pkg_names: List[str]) -> None:
    archive_dir = "_archives"
    for pkg_name in pkg_names:
        download_archive(archive_dir, normalize_pkg_name(pkg_name))


if __name__ == "__main__":
    main(sys.argv[1:])
