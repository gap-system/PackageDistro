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
`pkg_name/meta.json`. If no packages are given, all packages are downloaded.

If the archive already exists in the `_archives` directory and matches the
expected checksum, then it is not downloaded again.

Downloading an archive that fails to verify does not abort the run; the
remaining packages are still attempted, and a summary of the failures is
printed at the end.

Usage:

    > tools/download_packages.py digraphs walrus/meta.json
    _archives/digraphs-1.5.0.tar.gz already exists, not downloading again
    _archives/walrus-0.9991.tar.gz already exists, not downloading again

"""

import argparse
import os
import sys
from os.path import join
from typing import List

import requests
from utils import (
    all_packages,
    archive_name,
    archive_url,
    download,
    metadata,
    normalize_pkg_name,
    notice,
    sha256,
    warning,
)


class ChecksumError(Exception):
    """Raised when a downloaded archive does not have the expected checksum."""


def download_archive(archive_dir: str, pkg_name: str) -> str:
    """Returns the full archive name (including archive_dir) for the downloaded
    archive of the package `pkg_name`"""
    os.makedirs(archive_dir, exist_ok=True)

    pkg_json = metadata(pkg_name)
    expected_sha = pkg_json.get("ArchiveSHA256")
    archive_fname = join(archive_dir, archive_name(pkg_name))

    if os.path.isfile(archive_fname):
        archive_sha = sha256(archive_fname)
        if expected_sha is None or expected_sha == archive_sha:
            print(f"{archive_fname} already exists, not downloading again")
            return archive_fname
        notice(f"{archive_fname} has SHA256 {archive_sha}, expected {expected_sha}")

    url = archive_url(pkg_json)
    notice(f"downloading {url} to {archive_fname}")

    # Download to a temporary file next to the target, and only move it into
    # place once it has been verified. The archive directory may be served
    # directly by a web server (as it is on files.gap-system.org), where a
    # partially downloaded archive must never become visible. This also keeps
    # an existing, good archive intact if the download fails.
    tmp_fname = archive_fname + ".part"
    try:
        download(url, tmp_fname)
        if expected_sha is not None:
            actual_sha = sha256(tmp_fname)
            if actual_sha != expected_sha:
                raise ChecksumError(
                    f"{url} has SHA256 {actual_sha}, expected {expected_sha}"
                )
        os.replace(tmp_fname, archive_fname)
    except BaseException:
        if os.path.exists(tmp_fname):
            os.remove(tmp_fname)
        raise
    return archive_fname


def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "packages",
        nargs="*",
        help="packages to download (default: all packages)",
    )
    parser.add_argument(
        "--archive-dir",
        default="_archives",
        help="directory to download the archives into (default: _archives)",
    )
    args = parser.parse_args(argv)

    pkg_names = [normalize_pkg_name(p) for p in args.packages] or all_packages()

    failures: List[str] = []
    for pkg_name in pkg_names:
        try:
            download_archive(args.archive_dir, pkg_name)
        except (requests.RequestException, ChecksumError, OSError) as e:
            warning(f"{pkg_name}: {e}")
            failures.append(pkg_name)

    if failures:
        warning(f"failed to download {len(failures)} archive(s): {' '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
