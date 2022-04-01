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

import sys
import tempfile

from typing import List

from utils import download
from scan_for_updates import import_packages


def main(pkgs: List[str]) -> None:
    # each argument should either be...
    #  - the URL of a a PackageInfo.g file
    #  - the path to a PackageInfo.g file
    pkginfo_paths: List[str] = []
    for p in pkgs:
        if p.startswith("http://") or p.startswith("https://"):
            t = tempfile.mktemp(suffix=".g", prefix="pkginfo")
            print("downloading {} to tempfile {}".format(p, t))
            download(p, t)
            pkginfo_paths.append(t)
        else:
            pkginfo_paths.append(p)
    import_packages(pkginfo_paths)


if __name__ == "__main__":
    main(sys.argv[1:])
