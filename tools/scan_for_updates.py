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
This script is intended to iterate through package metadata in the repo:

      https://github.com/gap-system/PackageDistro

and do the following:

    TODO

"""

import hashlib
import json
import os
import requests
import sys
from os.path import join
from multiprocessing.pool import ThreadPool

from download_packages import download_archive

import utils
from utils import (
    notice,
    error,
    warning,
    all_packages,
    archive_url,
    metadata,
    metadata_fname,
    sha256,
    normalize_pkg_name,
)

from typing import Any, Dict, List, Optional

archive_dir = "_archives"
pkginfos_dir = "_pkginfos"


def download_to_memory(url: str) -> Optional[bytes]:
    response = requests.get(url)
    if response.status_code != 200:
        warning(
            f"error trying to download {url}, status code {response.status_code}, skipping!"
        )
        return None
    return response.content


def scan_for_one_update(pkginfos_dir: str, pkg_name: str) -> Optional[str]:
    pkg_json = metadata(pkg_name)
    try:
        hash_distro = pkg_json["PackageInfoSHA256"]
    except KeyError:
        notice(pkg_name + ': missing key "PackageInfoSHA256"')
        hash_distro = 0
    pkg_info = download_to_memory(pkg_json["PackageInfoURL"])
    if not isinstance(pkg_info, bytes):
        return None
    hash_url = hashlib.sha256(pkg_info).hexdigest()
    if hash_url != hash_distro:
        notice(pkg_name + ": detected different sha256 hash of PackageInfo.g")
        fname = join(pkginfos_dir, pkg_name + ".g")
        with open(fname, "wb") as f:
            f.write(pkg_info)
        return fname
    return None


def scan_for_updates(
    pkg_names: List[str],
    pkginfos_dir: str = pkginfos_dir,
    disable_threads: bool = False,
) -> list:
    if not os.path.exists(pkginfos_dir):
        os.mkdir(pkginfos_dir)
    assert os.path.isdir(pkginfos_dir)
    if disable_threads:
        result = [scan_for_one_update(pkginfos_dir, x) for x in pkg_names]
    else:
        result = ThreadPool(5).map(
            lambda x: scan_for_one_update(pkginfos_dir, x), pkg_names
        )
    return sorted([x for x in result if x != None])


def parse_pkginfo_files(pkginfo_paths: List[str]) -> List[Dict[str, Any]]:
    if len(pkginfo_paths) == 0:
        return []
    # get the path of this Python script, so that we can compute the path of
    # pkginfo_to_json.g (which should be in the same directory)
    dir_of_this_file = os.path.dirname(os.path.realpath(__file__))
    str = '", "'.join(pkginfo_paths)
    result, output = utils.gap_exec(
        f'OutputJson(["{str}"]);',
        args=f"{dir_of_this_file}/pkginfo_to_json.g",
    )
    if result != 0:
        error("Something went wrong")
    return json.loads(output)


def import_packages(pkginfo_paths: List[str]) -> None:
    pkginfos = parse_pkginfo_files(pkginfo_paths)
    for pkg_json in pkginfos:
        url = archive_url(pkg_json)
        archive_fname = join(archive_dir, url.split("/")[-1])
        utils.download(url, archive_fname)
        pkg_json["ArchiveSHA256"] = sha256(archive_fname)

        pkgname = pkg_json["PackageName"].lower()
        pkg_json_file = metadata_fname(pkgname)
        notice(f"update {pkg_json_file}")
        if not os.path.exists(os.path.dirname(pkg_json_file)):
            os.mkdir(os.path.dirname(pkg_json_file))
        with open(pkg_json_file, "w", encoding="utf-8") as f:
            json.dump(pkg_json, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")


def main(pkg_names: List[str]) -> None:
    print("Scanning for updates...")
    if len(pkg_names) == 0:
        pkg_names = all_packages()
    updated_pkgs = scan_for_updates(pkg_names)
    if len(updated_pkgs) == 0:
        print("None found")
        return
    print("Updating meta.json files...")
    import_packages(updated_pkgs)


if __name__ == "__main__":
    main([normalize_pkg_name(x) for x in sys.argv[1:]])
