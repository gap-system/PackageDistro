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

import sys
from typing import Any, Dict, List, Set

from utils import metadata, normalize_pkg_name

# The following maps names of GAP packages to lists of Ubuntu package names.
# The Ubuntu packages should be installed in order to build and/or use the GAP
# package. It serves as a fallback for those packages which do not yet set
# NeededSystemPackages in their package metadata.
#
# This map should be removed once it becomes empty.
ubtunu_deps = {
    "browse": ["libncurses5-dev"],
    "hap": ["graphviz", "imagemagick"],
}


def metadata_ubuntu_packages(pkg_json: Dict[str, Any]) -> Set[str]:
    system_packages = pkg_json["Dependencies"].get("NeededSystemPackages", {})
    return set(package_names[0] for package_names in system_packages.get("Ubuntu", []))


def ubuntu_packages(pkg_name: str, pkg_json: Dict[str, Any]) -> Set[str]:
    return set(ubtunu_deps.get(pkg_name, [])) | metadata_ubuntu_packages(pkg_json)


def gather_dependencies(pkg_name: str, seen: set) -> set:
    try:
        pkg_json = metadata(pkg_name)
    except:
        return set()
    seen.add(pkg_name)
    deps = ubuntu_packages(pkg_name, pkg_json)

    tmp = pkg_json["Dependencies"]
    gap_deps = tmp["NeededOtherPackages"]
    if "SuggestedOtherPackages" in tmp:
        gap_deps += tmp["SuggestedOtherPackages"]
    if "Extensions" in pkg_json:
        for ext in pkg_json["Extensions"]:
            gap_deps += ext["needed"]
    for pkg, _ in gap_deps:
        pkg = pkg.lower()
        # Ignore GAPDoc: TeX packages matter when testing GAPDoc itself, but
        # most recursive GAPDoc users only need it for documentation. See
        # https://github.com/gap-system/PackageDistro/issues/1400
        if not pkg in seen | {"gapdoc"}:
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
