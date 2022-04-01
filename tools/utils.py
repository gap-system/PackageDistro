#############################################################################
##
##  This file is part of GAP, a system for computational discrete algebra.
##
##  Copyright of GAP belongs to its developers, whose names are too numerous
##  to list here. Please refer to the COPYRIGHT file for details.
##
##  SPDX-License-Identifier: GPL-2.0-or-later
##
import hashlib
import json
import os
import requests
import subprocess
import sys
import tempfile

from os.path import join

from typing import Any, Dict, List, NoReturn, Tuple

# print notices in green
def notice(msg: str) -> None:
    print("\033[32m" + msg + "\033[0m")


# print warnings in yellow
def warning(msg: str) -> None:
    print("\033[33m" + msg + "\033[0m", file = sys.stderr)


# print error in red and exit
def error(msg: str) -> NoReturn: 
    print("\033[31m" + msg + "\033[0m", file = sys.stderr)
    sys.exit(1)

def all_packages() -> List[str]:
    pkgs = sorted(os.listdir(os.path.join(os.getcwd(), "packages")))
    return [d for d in pkgs if os.path.isfile(metadata_fname(d))]

def sha256(fname: str) -> str:
    hash_archive = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(16384), b""):
            hash_archive.update(chunk)
    return hash_archive.hexdigest()

def download(url: str, dst: str) -> None:
    """Download the file at the given URL `url` to the file with path `dst`."""
    response = requests.get(url, stream=True)
    with open(dst, "wb") as f:
        for chunk in response.raw.stream(16384, decode_content=False):
            if chunk:
                f.write(chunk)

def normalize_pkg_name(pkg_name: str) -> str:
    suffix = "/meta.json"
    prefix = "packages/"
    if pkg_name.startswith(prefix):
        pkg_name = pkg_name[len(prefix):]
    if pkg_name.endswith(suffix):
        pkg_name = pkg_name[:-len(suffix)]
    return pkg_name

def metadata_fname(pkg_name: str) -> str:
    return os.path.join("packages", pkg_name, "meta.json")

def metadata(pkg_name: str) -> Dict[str, Any]:
    fname = metadata_fname(pkg_name)
    pkg_json = {}

    try:
        with open(fname, "r", encoding="utf-8") as f:
            pkg_json = json.load(f)
    except (OSError, IOError):
        error("file {} not found".format(fname))
    except json.JSONDecodeError as e:
        error("invalid json in {}\n{}".format(fname, e.msg))
    return pkg_json


def archive_name(pkg_name: str) -> str:
    pkg_json = metadata(pkg_name)
    return (
        pkg_json["ArchiveURL"].split("/")[-1]
        + pkg_json["ArchiveFormats"].split(" ")[0]
    )


def archive_url(pkg_name: str) -> str:
    pkg_json = metadata(pkg_name)
    return pkg_json["ArchiveURL"] + pkg_json["ArchiveFormats"].split(" ")[0]

# https://stackoverflow.com/questions/8299386/modifying-a-symlink-in-python/55742015#55742015
def symlink(target: str, link_name: str, overwrite: bool = False) -> None:
    '''
    Create a symbolic link named link_name pointing to target.
    If link_name exists then FileExistsError is raised, unless overwrite=True.
    When trying to overwrite a directory, IsADirectoryError is raised.
    '''

    if not overwrite:
        os.symlink(target, link_name)
        return

    # os.replace() may fail if files are on different filesystems
    link_dir = os.path.dirname(link_name)

    # Create link to target with temporary filename
    while True:
        temp_link_name = tempfile.mktemp(dir=link_dir)

        # os.* functions mimic as closely as possible system functions
        # The POSIX symlink() returns EEXIST if link_name already exists
        # https://pubs.opengroup.org/onlinepubs/9699919799/functions/symlink.html
        try:
            os.symlink(target, temp_link_name)
            break
        except FileExistsError:
            pass

    # Replace link_name with temp_link_name
    try:
        # Pre-empt os.replace on a directory with a nicer message
        if not os.path.islink(link_name) and os.path.isdir(link_name):
            raise IsADirectoryError(f"Cannot symlink over existing directory: '{link_name}'")
        os.replace(temp_link_name, link_name)
    except:
        if os.path.islink(temp_link_name):
            os.remove(temp_link_name)
        raise


def gap_exec(commands: str, args: str = "") -> Tuple[int, bytes]:
    with subprocess.Popen(
        "gap -A -b --quitonbreak -q " + args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        shell=True,
    ) as GAP:
        out, err = GAP.communicate(input=commands.encode('utf-8'))
        return GAP.returncode, out
