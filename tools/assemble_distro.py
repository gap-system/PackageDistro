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
import io
import json
import os
import shutil
import subprocess
import sys
import typing
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional

from download_packages import download_archive
from utils import all_packages, error, metadata, normalize_pkg_name, sha256


def write_sha256(filename: str) -> None:
    with open(filename + ".sha256", "w") as f:
        f.write(sha256(filename))


def collect_package_info(pkgs: List[str]) -> Dict[str, Any]:
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
        # exclude ._* files, see <https://github.com/gap-system/PackageDistro/issues/1147>
        subprocess.run(
            ["tar", "czf", full_tarname, "--exclude", "._*", "-C", tempdir, "."]
        )
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
    package_info = collect_package_info(pkgs)
    package_infos_file = os.path.join(release_dir, "package-infos.json.gz")

    # create a GzipFile with mtime=0 to ensure reproducibility: re-running this
    # script should result in an identical .gz file (with same SHA256 checksum)
    binary_file = gzip.GzipFile(package_infos_file, "w", 9, mtime=0)
    # the next line is needed to make mypy happy, see <https://stackoverflow.com/a/58407810/928031>
    binary_file_for_mypy = typing.cast(typing.IO[bytes], binary_file)
    f_pkg_info = io.TextIOWrapper(binary_file_for_mypy, "utf-8", None, None)
    json.dump(package_info, f_pkg_info, indent=4)
    f_pkg_info.close()
    binary_file.close()
    write_sha256(package_infos_file)

    # also generate simple package list for PackageManager, see
    # https://github.com/gap-packages/PackageManager/issues/112
    pkglist = os.path.join(release_dir, "pkglist.csv")
    with open(pkglist, "w") as f:
        for pkg in pkgs:
            meta = package_info[pkg]
            f.write(meta["PackageName"])
            f.write("\t")
            f.write(meta["PackageInfoURL"])
            f.write("\n")


if __name__ == "__main__":
    main()
