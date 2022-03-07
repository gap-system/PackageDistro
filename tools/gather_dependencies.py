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

from accepts import accepts

from utils import normalize_pkg_name, metadata

# TODO: support other distros?
ubtunu_deps = {
'4ti2interface': [ '4ti2' ],
'alnuth': [ 'pari-gp' ],
'browse': [ 'libncurses5-dev' ],
'cddinterface': [ 'libcdd-dev' ],
'curlinterface': [ 'libcurl4-openssl-dev' ],
'float': [ 'libmpc-dev', 'libmpfi-dev', 'libmpfr-dev' ],
'normalizinterface': [ 'libnormaliz-dev' ],
'polymaking': [ 'polymake' ],
'singular': [ 'singular' ],
'zeromqinterface': [ 'libzmq3-dev' ],
}

@accepts(str, set)
def gather_dependencies(pkg_name: str, seen: set) -> None:
    pkg_json = metadata(pkg_name)
    seen.add(pkg_name)
    deps = set(ubtunu_deps.get(pkg_name, []))

    for pkg, _ in pkg_json["Dependencies"]["NeededOtherPackages"]:
        pkg = pkg.lower()
        if not pkg in seen:
            deps |= gather_dependencies(pkg, seen)
    return deps

def main(pkgs) -> None:
    seen = set()
    deps = set()
    for pkg in pkgs:
        deps |= gather_dependencies(normalize_pkg_name(pkg), seen)
    for d in deps:
        print(d)


if __name__ == "__main__":
    main(sys.argv[1:])
