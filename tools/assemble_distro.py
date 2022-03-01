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
import json
import shutil
import subprocess
import sys
import os
import gzip
from tempfile import TemporaryDirectory
from download_packages import download_archive, metadata_fname, normalize_pkg_name

from scan_for_updates import all_packages
from utils import sha256file


def make_package_info_json(pkgs):
    package_info = dict()
    for p in pkgs:
        with open(metadata_fname(p)) as f:
            package_info[p] = json.load(f)
    return package_info

def make_packages_tar_gz(archive_dir, release_dir, pkgs):
    # Check archive files are up to date
    archive_list = {}
    for p in pkgs:
        archive_list[p] = download_archive(archive_dir, p)

    # Don't put temporary directory in /tmp, as some machines have limited size.
    with TemporaryDirectory(dir=".") as tempdir:
        for pkg_name, pkg_archive in archive_list.items():
            print("Extracting tarball: ", pkg_archive)
            # Unpack into packagename-unpack
            unpack = tempdir + "/" + pkg_name + "-unpack"
            os.mkdir(unpack)
            shutil.unpack_archive(pkg_archive, unpack)
            # Check there is only one directory. Rename it to standardised name (pkg_name)
            pkgdirs = os.listdir(unpack)
            if len(pkgdirs) == 0:
                print("Error: no package directory found in archive: " + pkg_archive)
            elif len(pkgdirs) > 1:
                print("Error: more than one package directory found in archive: " + pkg_archive)
            else:
                os.rename(unpack + "/" + pkgdirs[0], unpack + "/" + pkg_name)
                os.rename(unpack + "/" + pkg_name, tempdir + "/" + pkg_name)
            os.rmdir(unpack)

        print("Creating final tarball: ", release_dir + "/packages.tar.gz")
        subprocess.run(["tar", "czf", release_dir + "/packages.tar.gz", "-C", tempdir, "."])
        with open(release_dir + "/packages.tar.gz.sha256", "w") as f:
            f.write(sha256file(release_dir + "/packages.tar.gz"))

def main():
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
    make_packages_tar_gz(archive_dir, release_dir, pkgs)

    # Make package-infos.json
    package_info = make_package_info_json(pkgs)
    with gzip.open(release_dir + "/package-infos.json.gz", "wt", encoding="utf-8") as f:
        json.dump(package_info, f, indent=4)
    with open(release_dir + "/package-infos.json.gz.sha256", "w") as f:
        f.write(sha256file(release_dir + "/package-infos.json.gz"))


if __name__ == "__main__":
    main()
