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
import subprocess
from os.path import join
from multiprocessing.pool import ThreadPool

from download_packages import download_archive

from utils import notice, error, warning, all_packages, metadata, metadata_fname, sha256, archive_name

from typing import Dict, Optional, Tuple

archive_dir = "_archives"
pkginfos_dir = "_pkginfos"

def download_pkg_info(pkg_name: str) -> Optional[bytes]:
    pkg_json = metadata(pkg_name)
    url = pkg_json["PackageInfoURL"]
    response = requests.get(url)
    if response.status_code != 200:
        warning(
            "error trying to download {}, status code {}, skipping!".format(
                url, response.status_code
            )
        )
        return None
    return response.content


def gap_exec(commands: str, args="") -> Tuple[int, bytes]:
    with subprocess.Popen(
        "gap -A -b --quitonbreak -q " + args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        shell=True,
    ) as GAP:
        out, err = GAP.communicate(input=commands.encode('utf-8'))
        return GAP.returncode, out


def scan_for_one_update(pkginfos_dir: str, pkg_name: str) -> Optional[str]:
    pkg_json = metadata(pkg_name)
    try:
        hash_distro = pkg_json["PackageInfoSHA256"]
    except KeyError:
        notice(pkg_name + ': missing key "PackageInfoSHA256"')
        hash_distro = 0
    pkg_info = download_pkg_info(pkg_name)
    if not isinstance(pkg_info, bytes):
        return None
    hash_url = hashlib.sha256(pkg_info).hexdigest()
    if hash_url != hash_distro:
        notice(pkg_name + ": detected different sha256 hash of PackageInfo.g")
        with open(join(pkginfos_dir, pkg_name + ".g"), "wb") as f:
            f.write(pkg_info)
        return pkg_name
    return None


def scan_for_updates(pkginfos_dir = pkginfos_dir, disable_threads = False):
    if not os.path.exists(pkginfos_dir):
        os.mkdir(pkginfos_dir)
    assert os.path.isdir(pkginfos_dir)
    if disable_threads:
        result = map(lambda x: scan_for_one_update(pkginfos_dir, x), all_packages())
    else: 
        result = ThreadPool(5).map(lambda x: scan_for_one_update(pkginfos_dir, x), all_packages())
    return sorted([x for x in result if x != None])


def output_json(updated_pkgs, pkginfos_dir = pkginfos_dir):
    dir_of_this_file = os.path.dirname(os.path.realpath(__file__))
    str = '", "'.join(updated_pkgs)
    result, _ = gap_exec(
            'OutputJson(["{}"], "{}");'.format(str, pkginfos_dir),
            args="{}/pkginfo_to_json.g".format(dir_of_this_file),
        )
    if result != 0:
        error("Something went wrong")


def download_package_archives(pkgs):
    archive_name_lookup = {}
    for pkgname in pkgs:
        # force a fresh download, in case upstream changed the archive in the meantime
        archive_fname = join(archive_dir, archive_name(pkgname))
        if os.path.exists(archive_fname):
            os.remove(archive_fname)
        archive_name_lookup[pkgname] = download_archive(archive_dir, pkgname)
    return archive_name_lookup


def add_sha256_to_json(updated_pkgs, archive_name_lookup):
    for pkgname in updated_pkgs:
        pkg_json_file = metadata_fname(pkgname)

        try:
            pkg_archive = archive_name_lookup[pkgname]
        except KeyError:
            notice("Could not locate archive for " + pkgname)
            continue
        pkg_json = {}
        with open(pkg_json_file, "rb") as f:
            pkg_json = json.load(f)
        pkg_json["PackageInfoSHA256"] = sha256(
            join(pkginfos_dir, pkgname + ".g")
        )
        pkg_json["ArchiveSHA256"] = sha256(pkg_archive)
        notice("update {0}".format(pkg_json_file))
        with open(pkg_json_file, "w", encoding="utf-8") as f:
            json.dump(pkg_json, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")


def main():
    print("Scanning for updates...")
    updated_pkgs = scan_for_updates()
    print(updated_pkgs)
    if len(updated_pkgs) == 0:
        print("None found")
        return
    print("Updating meta.json files...")
    output_json(updated_pkgs)
    archive_name_lookup = download_package_archives(updated_pkgs)
    add_sha256_to_json(updated_pkgs, archive_name_lookup)


if __name__ == "__main__":
    main()
