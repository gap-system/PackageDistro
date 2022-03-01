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

from download_packages import download_archive, metadata, normalize_pkg_name
from utils import error
from validate_package import unpack_archive


# TODO allow downloading of SuggestedPackages too
@accepts(str)
def download_dependencies(pkg_name: str) -> None:
    pkg_json = metadata(pkg_name)
    seen = set()
    pkgs_in_distro = set(os.listdir(os.getcwd()))

    for pkg, _ in pkg_json["Dependencies"]["NeededOtherPackages"]:
        pkg = pkg.lower()
        if not pkg in pkgs_in_distro:
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
            download_dependencies(pkg)


def main(pkgs) -> None:
    for pkg in pkgs:
        download_dependencies(normalize_pkg_name(pkg))


if __name__ == "__main__":
    main(sys.argv[1:])
