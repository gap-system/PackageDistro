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

Should be run after scan_for_updates.py. Arguments can be either package
names, or the path to a meta.json file. For example:

    _tools/validate_package.py  aclib digraphs walrus/meta.json
    aclib: _archives/aclib-1.3.2.tar.gz already exists, not downloading again
    aclib: unpacking _archives/aclib-1.3.2.tar.gz into _unpacked_archives ...
    aclib: current release version is 1.3.2, but previous release version was 1.3.2, FAILED!
    aclib: validation FAILED!
    digraphs: _archives/digraphs-1.5.0.tar.gz already exists, not downloading again
    digraphs: unpacking _archives/digraphs-1.5.0.tar.gz into _unpacked_archives ...
    digraphs: validated ok!
    walrus: _archives/walrus-0.9991.tar.gz already exists, not downloading again
    walrus: unpacking _archives/walrus-0.9991.tar.gz into _unpacked_archives ...
    walrus: the file walrus/meta.yml.old is missing, FAILED!
"""

import os
import sys
import shutil
from os.path import join

from accepts import accepts

from download_packages import archive_name, metadata, download_archive, normalize_pkg_name
from scan_for_updates import download_pkg_info, gap_exec, sha256
from utils import notice, warning


def unpack_archive(archive_dir, unpack_dir, pkg_name):
    archive_fname = join(archive_dir, archive_name(pkg_name))
    if not os.path.exists(unpack_dir):
        os.mkdir(unpack_dir)
    notice("unpacking {} into {} ...".format(archive_fname, unpack_dir))
    shutil.unpack_archive(archive_fname, unpack_dir)

def unpacked_archive_name(unpack_dir, pkg_name):
    for x in os.listdir(unpack_dir):
        if len(x) >= len(pkg_name) and x[: len(pkg_name)].lower() == pkg_name:
            return join(unpack_dir, x)
    warning("{}: couldn't determine the unpacked archive directory!")


def validate_package(archive_dir, unpack_dir, pkg_name):
    result = True

    pkg_json = metadata(pkg_name)

    pkg_info_name = join(
        unpacked_archive_name(unpack_dir, pkg_name), "PackageInfo.g"
    )

    if pkg_json["PackageInfoSHA256"] != sha256(pkg_info_name):
        warning(
            "{0}: {0}/meta.yml:PackageInfoSHA256 is not the SHA256 of {1}, FAILED!".format(
                pkg_name, pkg_info_name
            )
        )
        result = False

    packed_name = join(archive_dir, archive_name(pkg_name))

    if pkg_json["ArchiveSHA256"] != sha256(packed_name):
        warning(
            "{0}: {0}/meta.yml:ArchiveSHA256 is not the SHA256 of {1}, FAILED!".format(
                pkg_name, packed_name
            )
        )
        result = False

    if not os.path.exists(join(pkg_name, "meta.json.old")):
        notice(
            "{0}: the file {0}/meta.yml.old is not present, new package!".format(
                pkg_name
            )
        )

    return result
    # TODO: check SHA256 hashes for PackageinfoURL and archive are the same.


def main(pkg_name):
    unpack_dir = "_unpacked_archives"
    archive_dir = "_archives"

    download_archive(archive_dir, pkg_name)
    unpack_archive(archive_dir, unpack_dir, pkg_name)

    if validate_package(archive_dir, unpack_dir, pkg_name):
        dir_of_this_file = os.path.dirname(os.path.realpath(__file__))
        unpacked_name = unpacked_archive_name(unpack_dir, pkg_name)
        if (
            gap_exec(
                r"ValidatePackagesArchive(\"{}\", \"{}\");".format(
                    unpacked_name, pkg_name
                ),
                gap="gap {}/validate_package.g".format(dir_of_this_file),
            )
            != 0
        ):
            warning("{}: validation FAILED!".format(pkg_name))
        else:
            notice("{}: validated ok!".format(pkg_name))


if __name__ == "__main__":
    for i in range(1, len(sys.argv)):
        main(normalize_pkg_name(sys.argv[i]))
