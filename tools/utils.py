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
    print("\033[33m" + msg + "\033[0m")


# print error in red and exit
def error(msg):
    print("\033[31m" + msg + "\033[0m")
    sys.exit(1)


@accepts(str)
def skip(string: str) -> bool:
    return (
        string.startswith(".")
        or string.startswith("_")
        or string == "README.md"
    )

def all_packages():
    pkgs = sorted(os.listdir(os.getcwd()))
    return [d for d in pkgs if os.path.isdir(d) and os.path.isfile(metadata_fname(d)) and not skip(d)]

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
    if pkg_name.endswith(suffix):
        return pkg_name[:-len(suffix)]
    else:
        return pkg_name

@accepts(str)
def metadata_fname(pkg_name: str) -> str:
    return join(pkg_name, "meta.json")

@accepts(str)
def metadata(pkg_name: str) -> dict:
    fname = metadata_fname(pkg_name)
    pkg_json = {}

    try:
        with open(fname, "r", encoding="utf-8") as f:
            pkg_json = json.load(f)
    except (OSError, IOError):
        error("{}: file {} not found".format(pkg_name, fname))
    except json.JSONDecodeError as e:
        error("{}: invalid json in {}\n{}".format(pkg_name, fname, e.msg))
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
