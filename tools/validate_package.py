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

from download_packages import download_archive
from scan_for_updates import download_pkg_info, gap_exec

from utils import notice, warning, error, normalize_pkg_name, archive_name, metadata, sha256


def validate_tarball(filename):
    with tarfile.open(filename) as tf:
        names = tf.getnames()
        if len(names) == 0:
            error("tarball is empty")

        # no entry may contain ".."
        first = next(filter(lambda n: ".." in n, names), None)
        if first != None:
            error("tarball has bad entry {}".format(first))

        # get the basedir (all entries are supposed to be contained in that)
        basedir = names[0].split('/')[0]

        # all entries must either be equal to basedir or start with basedir+'/'
        first = next(filter(lambda n: basedir != n.split('/')[0], names), None)
        if first != None:
            error("tarball has entry {} outside of basedir {}".format(first, basedir))

        # must have a PackageInfo.g
        if not os.path.join(basedir, 'PackageInfo.g') in names:
            error("tarball is missing PackageInfo.g")

        return basedir


def validate_package(archive_fname, pkgdir, pkg_name):
    pkg_json = metadata(pkg_name)

    pkg_info_name = join(pkgdir, "PackageInfo.g")

    # verify the SHA256 for the PackageInfo.g that we recorded as PackageInfoSHA256
    # matches what is in the tarball
    if pkg_json["PackageInfoSHA256"] != sha256(pkg_info_name):
        error(
            "{0}/meta.yml:PackageInfoSHA256 is not the SHA256 of {1}".format(
                pkg_name, pkg_info_name
            )
        )

    if pkg_json["ArchiveSHA256"] != sha256(archive_fname):
        error(
            "{0}/meta.yml:ArchiveSHA256 is not the SHA256 of {1}".format(
                pkg_name, packed_name
            )
        )


def main(pkgs):
    archive_dir = "_archives"
    dir_of_this_file = os.path.dirname(os.path.realpath(__file__))

    with TemporaryDirectory() as tempdir:
        for pkg_name in pkgs:
            archive_fname = download_archive(archive_dir, pkg_name)
            pkgdir = join(tempdir, validate_tarball(archive_fname))
            shutil.unpack_archive(archive_fname, tempdir)
            validate_package(archive_fname, pkgdir, pkg_name)
            result, _ = gap_exec(
                    "ValidatePackagesArchive(\"{}\", \"{}\");".format(pkgdir, pkg_name),
                    args="{}/validate_package.g".format(dir_of_this_file),
                )
            if result != 0:
                error("{}: FAILED".format(pkg_name))
            else:
                notice("{}: PASSED".format(pkg_name))


if __name__ == "__main__":
    main([normalize_pkg_name(x) for x in sys.argv[1:]])
