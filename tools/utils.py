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
import sys

from accepts import accepts
from os.path import join


# print notices in green
def notice(msg):
    print("\033[32m" + msg + "\033[0m")


# print warnings in yellow
def warning(msg):
    print("\033[33m" + msg + "\033[0m", file = sys.stderr)


# print error in red and exit
def error(msg):
    print("\033[31m" + msg + "\033[0m", file = sys.stderr)
    sys.exit(1)

def all_packages():
    pkgs = sorted(os.listdir(os.path.join(os.getcwd(), "packages")))
    return [d for d in pkgs if os.path.isfile(metadata_fname(d))]

@accepts(str)
def sha256(fname: str) -> str:
    hash_archive = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(1024), b""):
            hash_archive.update(chunk)
    return hash_archive.hexdigest()

@accepts(str)
def normalize_pkg_name(pkg_name: str) -> str:
    suffix = "/meta.json"
    prefix = "packages/"
    if pkg_name.endswith(suffix) and pkg_name.startswith(prefix):
        return pkg_name[len(prefix):-len(suffix)]
    elif pkg_name.endswith(suffix):
        return pkg_name[:-len(suffix)]
    elif pkg_name.startswith(prefix):
        return pkg_name[len(prefix):]
    else:
        return pkg_name

@accepts(str)
def metadata_fname(pkg_name: str) -> str:
    return os.path.join("packages", pkg_name, "meta.json")

@accepts(str)
def metadata(pkg_name: str) -> dict:
    fname = metadata_fname(pkg_name)
    pkg_json = {}

    try:
        with open(fname, "r", encoding="utf-8") as f:
            pkg_json = json.load(f)
    except (OSError, IOError):
        error("file {} not found".format(pkg_name, fname))
    except json.JSONDecodeError as e:
        error("invalid json in {}\n{}".format(pkg_name, fname, e.msg))
    return pkg_json


@accepts(str)
def archive_name(pkg_name: str) -> str:
    pkg_json = metadata(pkg_name)
    return (
        pkg_json["ArchiveURL"].split("/")[-1]
        + pkg_json["ArchiveFormats"].split(" ")[0]
    )


@accepts(str)
def archive_url(pkg_name: str) -> str:
    pkg_json = metadata(pkg_name)
    return pkg_json["ArchiveURL"] + pkg_json["ArchiveFormats"].split(" ")[0]

# https://stackoverflow.com/questions/8299386/modifying-a-symlink-in-python/55742015#55742015
def symlink(target, link_name, overwrite=False):
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

def string_to_bool(string):
    if string.lower().strip() in ['1', 'true']:
        return True
    elif string.lower().strip() in ['0', 'false']:
        return False
    else:
        error("Unknown string representation of bool")