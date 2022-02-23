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

"""

import hashlib
import json
import os
import subprocess
import tarfile
import zipfile

import requests
from utils import error, notice, warning


def sha256(archive_fname):
    hash_archive = hashlib.sha256()
    with open(archive_fname, "rb") as f:
        for chunk in iter(lambda: f.read(1024), b""):
            hash_archive.update(chunk)
    return hash_archive.hexdigest()


def download_archive(pkg_name, url, archive_dir, archive_fname, tries=5):
    archive_ext = archive_fname.split(".")
    if archive_ext[-1] == "gz" or archive_ext[-1] == "bz2":
        archive_ext = "." + ".".join([archive_ext[-2], archive_ext[-1]])
    else:
        assert archive_ext[-1] == "zip"
        archive_ext = ".zip"

    archive_fname = os.path.join(archive_dir, archive_fname)
    notice("{}: downloaded {} to {}".format(pkg_name, url, archive_fname))

    for i in range(tries):
        try:
            response = requests.get(url, stream=True)
            with open(archive_fname, "wb") as f:
                for chunk in response.raw.stream(1024, decode_content=False):
                    if chunk:
                        f.write(chunk)
            return
        except:
            notice("{}: attempt {}/{} failed".format(pkg_name, i + 1, tries))


def unpack_archive(unpack_dir, archive_fname):
    if not os.path.exists(unpack_dir):
        os.mkdir(unpack_dir)
    ext = archive_fname.split(".")[0]
    notice("unpacking {} ...".format(archive_fname))

    if ext.endswith("gz") or ext.endswith("bz2"):
        with tarfile.open(archive_fname) as archive:
            archive.extractall(unpack_dir)
    elif ext.endswith("zip"):
        with zipfile.ZipFile(archive_fname) as archive:
            archive.extractall(unpack_dir)
    else:
        notice("unrecognized archive extension " + ext)


def gap_exec(commands, gap="gap"):
    assert isinstance(commands, str)
    assert isinstance(gap, str)

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


def scan_for_updates(archive_dir, pkginfos_dir, pkg_name):
    # TODO assumes we are in the root of the repo:
    # https://github.com/gap-system/PackageDistro
    if not os.path.exists(archive_dir):
        os.mkdir(archive_dir)
    assert os.path.isdir(archive_dir)
    if not os.path.exists(pkginfos_dir):
        os.mkdir(pkginfos_dir)
    assert os.path.isdir(pkginfos_dir)

    try:
        fname = os.path.join(pkg_name, "meta.json")
    except:
        notice(pkg_name + ": missing meta.json file, skipping!")
        return

    with open(fname, "r") as f:
        pkg_json = json.load(f)
        try:
            hash_distro = pkg_json["PackageInfoSHA256"]
        except KeyError:
            notice(pkg_name + ': missing key "PackageInfoSHA256"')
            hash_distro = 0
        url = pkg_json["PackageInfoURL"]
        response = requests.get(url)
        if response.status_code != 200:
            warning(
                "error trying to download {}, status code {}, skipping!".format(
                    url, response.status_code
                )
            )
            return
        hash_url = hashlib.sha256(response.text.encode("utf-8"))
        if hash_url != hash_distro:
            notice(pkg_name + ": detected different sha256 hash")
            fmt = pkg_json["ArchiveFormats"].split(" ")[0]
            url = pkg_json["ArchiveURL"] + fmt
            with open(os.path.join(pkginfos_dir, pkg_name + ".g"), "w") as f:
                f.write(response.text)
            download_archive(pkg_name, url, archive_dir, pkg_name + fmt)


def main():
    archive_dir = "_archives"
    json_dir = "_json"
    pkginfos_dir = "_pkginfos"
    for pkgname in sorted(os.listdir(os.getcwd())):
        if (
            not pkgname.startswith(".")
            and not pkgname.startswith("_")
            and os.path.isdir(pkgname)
        ):
            scan_for_updates(archive_dir, pkginfos_dir, pkgname)

    if (
        gap_exec(
            r"OutputJson(\"{}\", \"{}\");".format(pkginfos_dir, json_dir),
            gap="gap scan_for_updates.g",
        )
        != 0
    ):
        error("Something went wrong")

    for pkgname in sorted(os.listdir(os.getcwd())):
        if (
            not pkgname.startswith(".")
            and not pkgname.startswith("_")
            and os.path.isdir(pkgname)
        ):
            pkg_json_file = "{}/meta.json".format(json_dir)
            try:
                pkg_archive = next(
                    iter(
                        x
                        for x in os.listdir(archive_dir)
                        if x.startswith(pkgname)
                    )
                )
            except StopIteration:
                notice("Could not locate archive for " + pkgname)
                continue
            pkg_archive = "{}/{}".format(archive_dir, pkg_archive)
            pkg_json = {}
            with open(pkg_json_file, "r") as f:
                pkg_json = json.load(f)
            pkg_json["PackageInfoSHA256"] = sha256(
                os.path.join(pkginfos_dir, pkgname + ".g")
            )
            pkg_json["ArchiveSHA256"] = sha256(pkg_archive)
            with open(pkg_json_file, "w") as f:
                json.dump(pkg_json, f)


if __name__ == "__main__":
    main()
