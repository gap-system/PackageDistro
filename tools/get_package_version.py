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
This script takes the name of a GAP package and prints out its
version as stored in meta.json.
"""

import os
import sys

from utils import normalize_pkg_name, metadata

def get_version(pkg_name: str) -> str:
    pkg_json = metadata(pkg_name)
    return pkg_json["Version"]

def main(pkg) -> None:
    print(get_version(normalize_pkg_name(pkg)))


if __name__ == "__main__":
    main(sys.argv[1])
