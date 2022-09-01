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
This script takes a list of package names or meta.json file paths,
and prints a list of package names and package groups.

It obeys the following rules:
- if a package is NOT part of a group, then its name is printed
- if a package is part of a group, then the name of the group is printed
- no package or group name is printed more than once

The result is used by the `scan-for-updates.yml` GitHub workflow to produce
its job matrix: one job is started for each unique package OR group output
by this script.
"""

import sys

from typing import List, Set

from utils import normalize_pkg_name, metadata

"""
This dictionary maps source repository URLs to group names.
Packages are identified as being members of a group by their source repository URL.
"""
groups = {
    "https://github.com/homalg-project/CAP_project": "cap_project",
    "https://github.com/homalg-project/homalg_project": "homalg_project",
}


def is_group(pkg_or_group_name: str) -> bool:
    return pkg_or_group_name in groups.values()


def name_or_group(pkg_name: str) -> str:
    pkg_json = metadata(pkg_name)
    if "SourceRepository" in pkg_json:
        url = pkg_json["SourceRepository"]["URL"]
        if url in groups:
            return groups[url]
    return pkg_name


def main(pkgs: List[str]) -> None:
    all: Set[str] = set()
    for pkg in pkgs:
        all.add(name_or_group(normalize_pkg_name(pkg)))
    for n in all:
        print(n)


if __name__ == "__main__":
    main(sys.argv[1:])
