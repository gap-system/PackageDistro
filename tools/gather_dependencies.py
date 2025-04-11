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

"""
This script installs Ubuntu packages required by the GAP packages specified
on the command line.
"""

import os
import sys
from typing import List, Set

from utils import metadata, normalize_pkg_name

# The following maps names of GAP packages to lists of Ubuntu package names.
# The Ubuntu packages should be installed in order to build and/or use the GAP
# package
ubtunu_deps = {
    "4ti2interface": ["4ti2"],
    "alnuth": ["pari-gp"],
    "browse": ["libncurses5-dev"],
    "cddinterface": ["libcdd-dev"],
    "curlinterface": ["libcurl4-openssl-dev"],
    "float": ["libmpc-dev", "libmpfi-dev", "libmpfr-dev"],
    "gapdoc": [
        "texlive-latex-base",
        "texlive-latex-recommended",
        "texlive-latex-extra",
        "texlive-fonts-recommended",
    ],
    "localizeringforhomalg": ["singular"],
    "normalizinterface": ["libnormaliz-dev"],
    "polymaking": ["polymake"],
    "ringsforhomalg": ["singular"],
    "singular": ["singular"],
    "typeset": ["graphviz", "texlive", "preview-latex-style", "dot2tex"],
    "zeromqinterface": ["libzmq3-dev"],
}


def gather_dependencies(pkg_name: str, seen: set) -> set:
    try:
        pkg_json = metadata(pkg_name)
    except:
        return set()
    seen.add(pkg_name)
    deps = set(ubtunu_deps.get(pkg_name, []))

    tmp = pkg_json["Dependencies"]
    gap_deps = tmp["NeededOtherPackages"]
    if "SuggestedOtherPackages" in tmp:
        gap_deps += tmp["SuggestedOtherPackages"]
    for pkg, _ in gap_deps:
        pkg = pkg.lower()
        if not pkg in seen:
            deps |= gather_dependencies(pkg, seen)
    return deps


def main(pkgs: List[str]) -> None:
    seen: Set[str] = set()
    deps = set()
    for pkg in pkgs:
        deps |= gather_dependencies(normalize_pkg_name(pkg), seen)
    for d in deps:
        print(d)


if __name__ == "__main__":
    main(sys.argv[1:])
