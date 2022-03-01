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
import subprocess
from os.path import join

import requests
from accepts import accepts

from utils import error, notice, warning
from download_packages import download_archive, metadata


@accepts(str)
def skip(string: str) -> bool:
    return (
        string.startswith(".")
        or string.startswith("_")
        or string == "README.md"
    )


def all_packages():
    pkgs = sorted(os.listdir(os.getcwd()))
    return [d for d in pkgs if os.path.isdir(d) and os.path.isfile(join(d, 'meta.json')) and not skip(d)]


@accepts(str)
def sha256(fname: str) -> str:
    hash_archive = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(1024), b""):
            hash_archive.update(chunk)
    return hash_archive.hexdigest()


@accepts(str)
def download_pkg_info(pkg_name: str) -> str:
    pkg_json = metadata(pkg_name)
    url = pkg_json["PackageInfoURL"]
    response = requests.get(url)
    if response.status_code != 200:
        warning(
            "error trying to download {}, status code {}, skipping!".format(
                url, response.status_code
            )
        )
        return False
    response.encoding = "utf-8"
    return response.text.encode("utf-8")


@accepts(str, str)
def gap_exec(commands: str, gap="gap") -> int:

    with subprocess.Popen(
        r'echo "{}"'.format(commands),
        stdout=subprocess.PIPE,
        shell=True,
    ) as cmd:
        with subprocess.Popen(
            gap,
            stdin=cmd.stdout,
            shell=True,
            stdout=subprocess.DEVNULL,
        ) as GAP:
            GAP.wait()
            return GAP.returncode


@accepts(str, str)
def scan_for_one_update(pkginfos_dir: str, pkg_name: str) -> None:
    pkg_json = metadata(pkg_name)
    try:
        hash_distro = pkg_json["PackageInfoSHA256"]
    except KeyError:
        notice(pkg_name + ': missing key "PackageInfoSHA256"')
        hash_distro = 0
    pkg_info = download_pkg_info(pkg_name)
    if not pkg_info:
        return
    hash_url = hashlib.sha256(pkg_info).hexdigest()
    if hash_url != hash_distro:
        notice(pkg_name + ": detected different sha256 hash of PackageInfo.g")
        with open(join(pkginfos_dir, pkg_name + ".g"), "wb") as f:
            f.write(pkg_info)


@accepts(str)
def scan_for_updates(pkginfos_dir: str) -> None:
    if not os.path.exists(pkginfos_dir):
        os.mkdir(pkginfos_dir)
    assert os.path.isdir(pkginfos_dir)
    for pkgname in all_packages():
        scan_for_one_update(pkginfos_dir, pkgname)


@accepts(str)
def output_json(pkginfos_dir: str) -> None:
    dir_of_this_file = os.path.dirname(os.path.realpath(__file__))
    if (
        gap_exec(
            r"OutputJson(\"{}\");".format(pkginfos_dir),
            gap="gap {}/scan_for_updates.g".format(dir_of_this_file),
        )
        != 0
    ):
        error("Something went wrong")


@accepts(str, str)
def download_all_archives(archive_dir: str, pkginfos_dir: str) -> dict:
    if not os.path.exists(archive_dir):
        os.mkdir(archive_dir)
    assert os.path.isdir(archive_dir)
    archive_name_lookup = {}
    for pkginfo in sorted(os.listdir(pkginfos_dir)):
        if skip(pkginfo):
            continue
        pkgname = pkginfo.split(".")[0]
        archive_name_lookup[pkgname] = download_archive(archive_dir, pkgname)

    return archive_name_lookup


@accepts(str, dict)
def add_sha256_to_json(pkginfos_dir: str, archive_name_lookup: dict) -> None:
    for pkgname in sorted(os.listdir(pkginfos_dir)):
        if skip(pkgname):
            continue
        pkgname = pkgname.split(".")[0]
        pkg_json_file = "{}/meta.json".format(pkgname)

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
        notice("{0}: writing updated {0}/meta.json".format(pkgname))
        with open(pkg_json_file, "w", encoding="utf-8") as f:
            json.dump(pkg_json, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")


def main():
    archive_dir = "_archives"
    pkginfos_dir = "_pkginfos"

    scan_for_updates(pkginfos_dir)
    output_json(pkginfos_dir)
    archive_name_lookup = download_all_archives(archive_dir, pkginfos_dir)
    add_sha256_to_json(pkginfos_dir, archive_name_lookup)


if __name__ == "__main__":
    main()
