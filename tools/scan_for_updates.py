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

"""

import hashlib
import json
import os
import subprocess
import tarfile
import zipfile

import requests
from utils import error, notice, warning


def skip_dir(string):
    return (
        string.startswith(".")
        or string.startswith("_")
        or string == "README.md"
    )


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
    if os.path.exists(archive_fname) and os.path.isfile(archive_fname):
        notice(
            "{}: {} already exists, not downloading again".format(
                pkg_name, archive_fname
            )
        )
        return
    notice("{}: downloaded {} to {}".format(pkg_name, url, archive_fname))

    for i in range(tries):
        try:
            response = requests.get(url, stream=True)
            with open(archive_fname, "wb") as f:
                for chunk in response.raw.stream(1024, decode_content=False):
                    if chunk:
                        f.write(chunk)
            return
        except requests.RequestException:
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


def scan_for_one_update(archive_dir, pkginfos_dir, pkg_name):
    try:
        fname = os.path.join(pkg_name, "meta.json")
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
                with open(
                    os.path.join(pkginfos_dir, pkg_name + ".g"), "w"
                ) as f:
                    f.write(response.text)
                download_archive(pkg_name, url, archive_dir, pkg_name + fmt)
    except (OSError, IOError):
        notice(pkg_name + ": missing meta.json file, skipping!")
        return


def scan_for_updates(archive_dir, pkginfos_dir):
    if not os.path.exists(archive_dir):
        os.mkdir(archive_dir)
    assert os.path.isdir(archive_dir)
    if not os.path.exists(pkginfos_dir):
        os.mkdir(pkginfos_dir)
    assert os.path.isdir(pkginfos_dir)
    for pkgname in sorted(os.listdir(os.getcwd())):
        if not skip_dir(pkgname):
            scan_for_one_update(archive_dir, pkginfos_dir, pkgname)


def output_json(pkginfos_dir):
    if (
        gap_exec(
            r"OutputJson(\"{}\");".format(pkginfos_dir),
            gap="gap _tools/scan_for_updates.g",
        )
        != 0
    ):
        error("Something went wrong")


def add_sha256_to_json(archive_dir, pkginfos_dir):
    for pkgname in sorted(os.listdir(os.getcwd())):
        if not skip_dir(pkgname):
            pkg_json_file = "{}/meta.json".format(pkgname)
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


def main():
    archive_dir = "_archives"
    pkginfos_dir = "_pkginfos"

    scan_for_updates(archive_dir, pkginfos_dir)
    output_json(pkginfos_dir)
    add_sha256_to_json(archive_dir, pkginfos_dir)


if __name__ == "__main__":
    main()
