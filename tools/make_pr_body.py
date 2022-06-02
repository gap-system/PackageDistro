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

import utils

from typing import List


def main(pkg_names: List[str]) -> None:
    if len(pkg_names) != 1:
        utils.error("must be called with exactly one package name")
    pkg_json = utils.metadata(pkg_names[0])
    print("Relevant links")
    print(f"""- [website]({pkg_json["PackageWWWHome"]})""")
    if "IssueTrackerURL" in pkg_json:
        print(f"""- [issue tracker]({pkg_json["IssueTrackerURL"]})""")
    else:
        print(f"""- no issue tracker specified""")

    if "SourceRepository" in pkg_json:
        print(f"""- [source repository]({pkg_json["SourceRepository"]["URL"]})""")
    else:
        print(f"""- no source repository specified""")
    print(f"""- [PackageInfo.g]({pkg_json["PackageInfoURL"]})""")
    print(f"""- [README]({pkg_json["README_URL"]})""")
    print(f"""- [source archive]({utils.archive_url(pkg_json)})""")


if __name__ == "__main__":
    main([utils.normalize_pkg_name(x) for x in sys.argv[1:]])
