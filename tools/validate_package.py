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
Runs some basic validation of the pkgname/meta.json against the package
archive, and the old meta data.

Should be run after scan_for_updates.py. Arguments can be either a package
name, or the path to a meta.json file. For example:

    $ tools/validate_package.py aclib digraphs walrus/meta.json
    aclib: _archives/aclib-1.3.2.tar.gz already exists, not downloading again
    aclib: unpacking _archives/aclib-1.3.2.tar.gz into _unpacked_archives ...
    aclib: current release version is 1.3.2, but previous release version was 1.3.2
    aclib: validation FAILED!
    $ tools/validate_package.py digraphs
    digraphs: _archives/digraphs-1.5.0.tar.gz already exists, not downloading again
    digraphs: unpacking _archives/digraphs-1.5.0.tar.gz into _unpacked_archives ...
    digraphs: validated ok!
    $ tools/validate_package.py walrus/meta.json
    walrus: _archives/walrus-0.9991.tar.gz already exists, not downloading again
    walrus: unpacking _archives/walrus-0.9991.tar.gz into _unpacked_archives ...
    walrus: the file walrus/meta.yml.old is missing, FAILED!
"""

import os
import sys
import shutil
import tarfile
from os.path import join
from tempfile import TemporaryDirectory

from typing import List

from download_packages import download_archive
from scan_for_updates import download_to_memory

import utils
from utils import (
    notice,
    warning,
    error,
    normalize_pkg_name,
    archive_name,
    metadata,
    sha256,
)


def validate_tarball(filename: str) -> str:
    with tarfile.open(filename) as tf:
        names = tf.getnames()
        if len(names) == 0:
            error("tarball is empty")

        # no entry may contain ".."
        first = next(filter(lambda n: ".." in n, names), None)
        if first != None:
            error(f"tarball has bad entry {first}")

        # get the basedir (all entries are supposed to be contained in that)
        basedir = names[0].split("/")[0]

        # all entries must either be equal to basedir or start with basedir+'/'
        badentries = filter(lambda n: basedir != n.split("/")[0], names)
        first = next(badentries, None)
        if first != None:
            error(f"tarball has entry {first} outside of basedir {basedir}")

        # must have a PackageInfo.g
        if not os.path.join(basedir, "PackageInfo.g") in names:
            error("tarball is missing PackageInfo.g")

        return basedir


def validate_package(archive_fname: str, pkgdir: str, pkg_name: str) -> None:
    pkg_json = metadata(pkg_name)

    # validate Status
    status = pkg_json["Status"]
    if not status in ["accepted", "deposited"]:
        error(f"{pkg_name}: Status is {status}, should be 'accepted' or 'deposited'")

    # validate PackageInfoURL
    data = download_to_memory(pkg_json["PackageInfoURL"])
    if data == None:
        error("PackageInfoURL is invalid")

    # validate README_URL
    data = download_to_memory(pkg_json["README_URL"])
    if data == None:
        error("README_URL is invalid")

    # verify the SHA256 for the PackageInfo.g that we recorded as PackageInfoSHA256
    # matches what is in the tarball
    pkg_info_name = join(pkgdir, "PackageInfo.g")
    if pkg_json["PackageInfoSHA256"] != sha256(pkg_info_name):
        error(f"{pkg_name}: PackageInfoSHA256 is not the SHA256 of {pkg_info_name}")

    # verify the SHA256 for archive that we recorded as ArchiveSHA256
    if pkg_json["ArchiveSHA256"] != sha256(archive_fname):
        error(f"{pkg_name}: ArchiveSHA256 is not the SHA256 of {archive_fname}")


def main(pkgs: List[str]) -> None:
    archive_dir = "_archives"
    dir_of_this_file = os.path.dirname(os.path.realpath(__file__))

    with TemporaryDirectory() as tempdir:
        for pkg_name in pkgs:
            archive_fname = download_archive(archive_dir, pkg_name)
            pkgdir = join(tempdir, validate_tarball(archive_fname))
            shutil.unpack_archive(archive_fname, tempdir)
            validate_package(archive_fname, pkgdir, pkg_name)
            result, _ = utils.gap_exec(
                f'ValidatePackagesArchive("{pkgdir}", "{pkg_name}");',
                args=f"{dir_of_this_file}/validate_package.g",
            )
            if result != 0:
                error(f"{pkg_name}: FAILED")
            else:
                notice(f"{pkg_name}: PASSED")


if __name__ == "__main__":
    main([normalize_pkg_name(x) for x in sys.argv[1:]])
