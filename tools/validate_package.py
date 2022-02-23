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
This script is intended to iterate through package metadata in the repo:

      https://github.com/gap-system/PackageDistro

and do the following:

"""

import json
import os
import shutil
import tarfile
import zipfile
from os.path import join

from _tools.scan_for_updates import download_archive, gap_exec
from _tools.utils import notice


def unpack_archive(unpack_dir, archive_fname):
    if not os.path.exists(unpack_dir):
        os.mkdir(unpack_dir)
    ext = archive_fname.split(".")[-1]
    notice("unpacking {} ...".format(archive_fname))

    if ext.endswith("gz") or ext.endswith("bz2"):
        with tarfile.open(archive_fname) as archive:
            archive.extractall(unpack_dir)
    elif ext.endswith("zip"):
        with zipfile.ZipFile(archive_fname) as archive:
            archive.extractall(unpack_dir)
    else:
        notice(
            "bad archive extension {}, skipping {}".format(ext, archive_fname)
        )


def get_unpacked_archive_dirname(pkg_name):
    for x in os.listdir("_tmp"):
        if len(x) >= len(pkg_name) and x[: len(pkg_name)].lower() == pkg_name:
            return x


def main(pkg_name):

    fname = join(pkg_name, "meta.json")
    try:
        pkg_json = {}
        with open(fname, "r") as f:
            pkg_json = json.load(f)
    except (OsError, IOError):
        error("{}: cannot locate {}".format(pkg_name, fname))

    fmt = pkg_json["ArchiveFormats"].split(" ")[0]
    url = pkg_json["ArchiveURL"] + fmt
    archive_name = pkg_name + fmt
    download_archive(pkg_name, url, "_archives", archive_name, tries=5)
    unpack_archive("_tmp", join("_archives", archive_name))
    unpacked_dir = get_unpacked_archive_dirname(pkg_name)
    shutil.move(join("_tmp", unpacked_dir), join("_tmp", pkg_name))


if __name__ == "__main__":
    main()
