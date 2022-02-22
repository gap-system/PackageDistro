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
This script is intended to iterate through package metadata in the repo:

      https://github.com/gap-system/PackageDistro

and do the following:

    * extract the `PackageInfoURL` and `PackageInfoSHA256` fields from the
      metadata
    * download the `PackageInfo.g` file from the URL, find the sha256 of the
      file, and compare it to the one in the metadata.
    * if the sha256 hashes differ, then write the downloaded `PackageInfo.g`
      file to `_tmp/package_name.g`

usage:

    import scan_for_updates
    scan_for_updates.main()
    4ti2interface: missing key "PackageInfoSHA256"
    4ti2interface: detected different sha256 hash
    ace: missing key "PackageInfoSHA256"
    ace: detected different sha256 hash
    ...
"""

import hashlib
import json
import os
import subprocess
import sys

import requests
from utils import error, notice, warning


def scan_for_updates(pkg_name):
    # TODO assumes we are in the root of the repo:
    # https://github.com/gap-system/PackageDistro
    tmp_dir = "_tmp"
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
    assert os.path.isdir("_tmp")
    try:
        fname = os.path.join(pkg_name, pkg_name + ".json")
    except:
        notice(pkg_name + ": missing {}.json file, skipping!".format(pkg_name))
        return

    with open(fname, "r") as f:
        pkg_json = json.load(f)
        try:
            hash_distro = pkg_json["PackageInfoSHA256"]
        except KeyError:
            notice(pkg_name + ': missing key "PackageInfoSHA256"')
            hash_distro = 0
        url = pkg_json["PackageInfoURL"]
        html_response = requests.get(url)
        if html_response.status_code != 200:
            warning(
                "error trying to download {}, status code {}, skipping!".format(
                    url, html_response.status_code
                )
            )
            return
        hash_url = hashlib.sha256(html_response.text.encode("utf-8"))
        if hash_url != hash_distro:
            notice(pkg_name + ": detected different sha256 hash")
            pkg_info_fname = os.path.join(tmp_dir, pkg_name + ".g")
            with open(pkg_info_fname, "w") as pif:
                pif.write(html_response.text)


def main():
    for x in sorted(os.listdir(os.getcwd())):
        if not x.startswith(".") and not x.startswith("_") and os.path.isdir(x):
            scan_for_updates(x)


if __name__ == "__main__":
    main()
