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
import requests

from accepts import accepts
from os.path import join

from typing import NoReturn

# print notices in green
def notice(msg):
    print("\033[32m" + msg + "\033[0m")


# print warnings in yellow
def warning(msg):
    print("\033[33m" + msg + "\033[0m", file = sys.stderr)


# print error in red and exit
def error(msg) -> NoReturn: 
    print("\033[31m" + msg + "\033[0m", file = sys.stderr)
    sys.exit(1)

def all_packages():
    pkgs = sorted(os.listdir(os.path.join(os.getcwd(), "packages")))
    return [d for d in pkgs if os.path.isfile(metadata_fname(d))]

@accepts(str)
def sha256(fname: str) -> str:
    hash_archive = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(16384), b""):
            hash_archive.update(chunk)
    return hash_archive.hexdigest()

@accepts(str, str)
def download(url: str, dst: str) -> None:
    """Download the file at the given URL `url` to the file with path `dst`."""
    response = requests.get(url, stream=True)
    with open(dst, "wb") as f:
        for chunk in response.raw.stream(16384, decode_content=False):
            if chunk:
                f.write(chunk)

@accepts(str)
def normalize_pkg_name(pkg_name: str) -> str:
    suffix = "/meta.json"
    prefix = "packages/"
    if pkg_name.startswith(prefix):
        pkg_name = pkg_name[len(prefix):]
    if pkg_name.endswith(suffix):
        pkg_name = pkg_name[:-len(suffix)]
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
        error("file {} not found".format(fname))
    except json.JSONDecodeError as e:
        error("invalid json in {}\n{}".format(fname, e.msg))
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
