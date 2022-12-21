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
import glob
import gzip
import json
import os
import shutil
import subprocess
import sys

from tempfile import TemporaryDirectory
from download_packages import download_archive

from utils import error, normalize_pkg_name, metadata, sha256, all_packages

from typing import Any, Dict, List, Optional


def write_sha256(filename: str) -> None:
    with open(filename + ".sha256", "w") as f:
        f.write(sha256(filename))


def make_package_info_json(pkgs: List[str]) -> Dict[str, Any]:
    package_info = dict()
    for p in pkgs:
        package_info[p] = metadata(p)
    return package_info


def make_packages_tar_gz(
    tarname: str, archive_dir: str, release_dir: str, pkgs: List[str]
) -> None:
    # Check archive files are up to date
    archive_list = {}
    for p in pkgs:
        archive_list[p] = download_archive(archive_dir, p)

    # Don't put temporary directory in /tmp, as some machines have limited size.
    with TemporaryDirectory(dir=".") as tempdir:
        for pkg_name, pkg_archive in archive_list.items():
            print("Extracting tarball: ", pkg_archive)
            # Unpack into packagename-unpack
            unpack = os.path.join(tempdir, pkg_name + "-unpack")
            os.mkdir(unpack)
            shutil.unpack_archive(pkg_archive, unpack)
            # Check there is only one directory. Rename it to standardised name (pkg_name)
            pkgdirs = os.listdir(unpack)
            if len(pkgdirs) == 0:
                error("Error: no package directory found in archive: " + pkg_archive)
            elif len(pkgdirs) > 1:
                error(
                    "Error: more than one package directory found in archive: "
                    + pkg_archive
                )
            else:
                os.rename(
                    os.path.join(unpack, pkgdirs[0]), os.path.join(unpack, pkg_name)
                )
                os.rename(
                    os.path.join(unpack, pkg_name), os.path.join(tempdir, pkg_name)
                )
            os.rmdir(unpack)

        # cleanup step: remove all PACKAGE/doc/*.aux etc. etc. files
        for ext in [
            "aux",
            "bbl",
            "blg",
            "brf",
            "idx",
            "ilg",
            "ind",
            "log",
            "out",
            "pnr",
            "toc",
        ]:
            for f in glob.glob(f"{tempdir}/*/doc/*.{ext}"):
                os.remove(f)

        # WORKAROUND: remove any symlinks. Actually we reject package updates with
        # symlinks, but there is one package (AGT) which currently ships a broken
        # symlink
        for subdir, dirs, files in os.walk(tempdir):
            for file in files:
                filepath = os.path.join(subdir, file)
                if os.path.islink(filepath):
                    os.unlink(filepath)

        full_tarname = os.path.join(release_dir, tarname)
        print("Creating final tarball: ", full_tarname)
        subprocess.run(["tar", "czf", full_tarname, "-C", tempdir, "."])
        write_sha256(full_tarname)


def main() -> None:
    archive_dir = "_archives"
    release_dir = "_releases"

    if not os.path.exists(release_dir):
        os.mkdir(release_dir)

    pkgs = sys.argv[1:]
    if len(pkgs) == 0:
        pkgs = all_packages()
    else:
        pkgs = [normalize_pkg_name(x) for x in pkgs]

    # Make packages.tar.gz
    make_packages_tar_gz("packages.tar.gz", archive_dir, release_dir, pkgs)
    make_packages_tar_gz(
        "packages-required.tar.gz",
        archive_dir,
        release_dir,
        ["gapdoc", "primgrp", "smallgrp", "transgrp"],
    )

    # Make package-infos.json
    package_info = make_package_info_json(pkgs)
    package_infos_file = os.path.join(release_dir, "package-infos.json.gz")
    with gzip.open(package_infos_file, "wt", encoding="utf-8") as f:
        json.dump(package_info, f, indent=4)
    write_sha256(package_infos_file)


if __name__ == "__main__":
    main()
