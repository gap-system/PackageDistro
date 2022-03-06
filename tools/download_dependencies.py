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
This script downloads the dependencies of the command line arguments.
"""

import os
import sys

from accepts import accepts

from download_packages import download_archive
from validate_package import unpack_archive

from utils import error, normalize_pkg_name, metadata, metadata_fname

# TODO allow downloading of SuggestedPackages too
@accepts(str, set)
def download_dependencies(pkg_name: str, seen: set) -> None:
    pkg_json = metadata(pkg_name)
    seen.add(pkg_name)

    for pkg, _ in pkg_json["Dependencies"]["NeededOtherPackages"]:
        pkg = pkg.lower()
        if not os.path.isfile(metadata_fname(pkg)):
            error(
                "{}: dependency {} not in distro, giving up!".format(
                    pkg_name, pkg
                )
            )
        # TODO fail if required version number in PackageInfo.g is higher than
        # the version in the distro
        if not pkg in seen:
            seen.add(pkg)
            download_archive("_archives", pkg)
            unpack_archive("_archives", "_unpacked_archives", pkg)
            download_dependencies(pkg, seen)


def main(pkgs) -> None:
    for pkg in pkgs:
        download_dependencies(normalize_pkg_name(pkg), set())


if __name__ == "__main__":
    main(sys.argv[1:])
