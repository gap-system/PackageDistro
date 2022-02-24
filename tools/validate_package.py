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
TODO
"""

import json
import os
import shutil
import sys
import tarfile
import zipfile
from os.path import join

from scan_for_updates import download_archive, gap_exec, metadata, sha256
from utils import error, notice, warning


def unpack_archive(unpack_dir, pkg_name, archive_fname):
    if not os.path.exists(unpack_dir):
        os.mkdir(unpack_dir)
    ext = archive_fname.split(".")[-1]
    notice(
        "{}: unpacking {} into {} ...".format(
            pkg_name, archive_fname, unpack_dir
        )
    )

    if ext.endswith("gz") or ext.endswith("bz2"):
        with tarfile.open(archive_fname) as archive:
            archive.extractall(unpack_dir)
    elif ext.endswith("zip"):
        with zipfile.ZipFile(archive_fname) as archive:
            archive.extractall(unpack_dir)
    else:
        notice(
            "{}: bad archive extension {}, skipping {}".format(
                pkg_name, ext, archive_fname
            )
        )


def unpacked_archive_name(unpack_dir, pkg_name):
    for x in os.listdir(unpack_dir):
        if len(x) >= len(pkg_name) and x[: len(pkg_name)].lower() == pkg_name:
            return x
    warning("{}: couldn't determine the unpacked archive directory!")


def archive_name(archive_dir, pkg_name):
    for x in os.listdir(archive_dir):
        if len(x) >= len(pkg_name) and x[: len(pkg_name)].lower() == pkg_name:
            return x
    warning("{}: couldn't determine the archive name!")


def validate_package(pkg_name, unpacked_name, packed_name, pkg_json):
    result = True
    pkg_info_name = join(unpacked_name, "PackageInfo.g")

    if pkg_json["PackageInfoSHA256"] != sha256(pkg_info_name):
        warning(
            "{0}: {0}/meta.yml:PackageInfoSHA256 is not the SHA256 of {1}!".format(
                pkg_name, pkg_info_name
            )
        )
        result = False

    if pkg_json["ArchiveSHA256"] != sha256(packed_name):
        warning(
            "{0}: {0}/meta.yml:ArchiveSHA256 is not the SHA256 of {1}!".format(
                pkg_name, packed_name
            )
        )
        result = False

    if not os.path.exists(join(pkg_name, "meta.json.old")):
        error(
            "{0}: the file {0}/meta.yml.old is missing, failed!".format(
                pkg_name
            )
        )

    return result
    # TODO: check SHA256 hashes for PackageinfoURL and archive are the same.


def main(pkg_name):
    unpack_dir = "_unpacked_archives"
    archive_dir = "_archives"

    pkg_json = metadata(pkg_name)

    fmt = pkg_json["ArchiveFormats"].split(" ")[0]
    url = pkg_json["ArchiveURL"] + fmt

    packed_name = pkg_json["ArchiveURL"].split("/")[-1] + fmt
    download_archive(pkg_name, url, archive_dir, packed_name, tries=5)

    unpack_archive(unpack_dir, pkg_name, join(archive_dir, packed_name))
    unpacked_name = join(
        unpack_dir, unpacked_archive_name(unpack_dir, pkg_name)
    )

    if validate_package(
        pkg_name,
        unpacked_name,
        join(archive_dir, packed_name),
        pkg_json,
    ):
        dir_of_this_file = os.path.dirname(os.path.realpath(__file__))
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
        main(sys.argv[i])
