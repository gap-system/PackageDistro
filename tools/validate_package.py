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
import shutil
import sys
import tarfile
from os.path import join
from tempfile import TemporaryDirectory
from typing import List

import utils
from download_packages import download_archive
from utils import (
    archive_name,
    download_to_memory,
    error,
    metadata,
    normalize_pkg_name,
    notice,
    sha256,
    warning,
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

        # must not contain symlinks (these often cause trouble on Windows).
        # TODO: if anyone ever really needs symlinks, then at the very least
        # we should prevent symlinks pointing outside the package directory.
        symlinks = [x for x in tf.getnames() if tf.getmember(x).issym()]
        if len(symlinks) > 0:
            error(f"tarball contains symlinks: {symlinks}")

        return basedir


def validate_package(archive_fname: str, pkgdir: str, pkg_name: str) -> None:
    pkg_json = metadata(pkg_name)

    # validate PackageInfoURL (download_to_memory raises an exception if download fails)
    data = download_to_memory(pkg_json["PackageInfoURL"])
    # We deliberately do not compare the SHA256 of `data` against PackageInfoSHA256
    # as it may be that a different version of the package was released in the meantime

    # validate README_URL (download_to_memory raises an exception if download fails)
    data = download_to_memory(pkg_json["README_URL"])
    # We could compare the SHA256 of `data` against the README in the package archive,
    # but this is really unimportant, so it's simpler for everyone to just let mistakes
    # here slide (there is an argument to be made that we should just drop README_URL
    # completely anyway)

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
            try:
                archive_fname = download_archive(archive_dir, pkg_name)
                pkgdir = join(tempdir, validate_tarball(archive_fname))
                shutil.unpack_archive(archive_fname, tempdir)
                validate_package(archive_fname, pkgdir, pkg_name)
                result, _ = utils.gap_exec(
                    f'ValidatePackagesArchive("{pkgdir}", "{pkg_name}");',
                    args=f"{dir_of_this_file}/validate_package.g",
                )
                if result != 0:
                    error(f"{pkg_name}: FAILED: ValidatePackagesArchive failed")
            except Exception as e:
                error(f"{pkg_name}: FAILED: {e}")
            notice(f"{pkg_name}: PASSED")


if __name__ == "__main__":
    main([normalize_pkg_name(x) for x in sys.argv[1:]])
