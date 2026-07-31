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
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from os.path import join
from typing import Any, Dict, List, NoReturn, Tuple

import requests

# Timeouts in seconds, as (connect, read). Without these, a stalled connection
# blocks forever, which matters for unattended runs (e.g. the mirror on
# files.gap-system.org). Both are deliberately generous: the point is to bound
# a hang, not to enforce a fast connection. Poor networks have been observed
# taking over 20 seconds just to connect to the host serving GitHub release
# assets, and the read timeout applies between reads, not to the whole
# download, so a large archive on a slow link is fine.
DOWNLOAD_TIMEOUT = (30, 60)

# How many times to attempt a download before giving up. Only transient
# failures are retried; see `_should_retry`.
DOWNLOAD_ATTEMPTS = 3


# print notices in green
def notice(msg: str) -> None:
    print("\033[32m" + msg + "\033[0m")


# print warnings in yellow
def warning(msg: str) -> None:
    print("\033[33m" + msg + "\033[0m", file=sys.stderr)


# print error in red and exit
def error(msg: str) -> NoReturn:
    print("\033[31m" + msg + "\033[0m", file=sys.stderr)
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


def _should_retry(e: requests.RequestException) -> bool:
    """Return whether the failed request `e` is worth retrying.

    Connection problems and timeouts are transient. So are HTTP 429 (rate
    limited) and 5xx responses. Anything else -- notably a 404 -- will fail the
    same way again, so retrying only wastes time.
    """
    if isinstance(e, requests.HTTPError) and e.response is not None:
        return e.response.status_code == 429 or e.response.status_code >= 500
    return isinstance(e, (requests.ConnectionError, requests.Timeout))


def download(url: str, dst: str) -> None:
    """Download the file at the given URL `url` to the file with path `dst`.

    Transient failures are retried; if every attempt fails, the underlying
    `requests.RequestException` is raised.
    """
    dst_dir = os.path.dirname(dst)
    if dst_dir:
        os.makedirs(dst_dir, exist_ok=True)
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            response = requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)
            response.raise_for_status()  # raise a meaningful (?) exception if there was e.g. a 404 error
            with open(dst, "wb") as f:
                for chunk in response.raw.stream(16384, decode_content=True):
                    if chunk:
                        f.write(chunk)
            return
        except requests.RequestException as e:
            if attempt == DOWNLOAD_ATTEMPTS or not _should_retry(e):
                raise
            warning(f"downloading {url} failed ({e}), retrying")
            time.sleep(2**attempt)


def unpack_archive(archive: str, dst: str) -> None:
    """Unpack the archive `archive` into the directory `dst`.

    Tar archives are extracted using the "data" extraction filter, which
    refuses entries that would write outside `dst`. Python 3.14 applies that
    filter by default and warns about relying on the old, unfiltered behaviour;
    naming it here keeps extraction identical across Python versions.

    Extraction filters are a tar concept, and `shutil` rejects the argument for
    other formats, so zip archives are simply unpacked as before.
    """
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive) as tf:
            tf.extractall(dst, filter="data")
    else:
        shutil.unpack_archive(archive, dst)


def download_to_memory(url: str) -> bytes:
    response = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
    response.raise_for_status()
    return response.content


def normalize_pkg_name(pkg_name: str) -> str:
    suffix = "/meta.json"
    prefix = "packages/"
    if pkg_name.startswith(prefix):
        pkg_name = pkg_name[len(prefix) :]
    if pkg_name.endswith(suffix):
        pkg_name = pkg_name[: -len(suffix)]
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
        error(f"file {fname} not found")
    except json.JSONDecodeError as e:
        error(f"invalid json in {fname}\n{e.msg}")
    return pkg_json


# Archive formats to put first, in order of preference. Our own tooling uses
# the first format listed in `ArchiveFormats`: it is the archive we download,
# checksum, redistribute and mirror to files.gap-system.org, and hence the only
# one guaranteed to be available from there. Prefer .tar.gz as the most widely
# supported -- some consumers cannot unpack .tar.bz2 at all.
PREFERRED_ARCHIVE_FORMATS = [".tar.gz"]


def sort_archive_formats(formats: str) -> str:
    """Reorder a space separated `ArchiveFormats` value, preferred formats first.

    Formats we have no opinion about keep their original relative order.
    """
    rank = {fmt: i for i, fmt in enumerate(PREFERRED_ARCHIVE_FORMATS)}
    unranked = len(PREFERRED_ARCHIVE_FORMATS)
    return " ".join(sorted(formats.split(), key=lambda f: rank.get(f, unranked)))


def archive_format(pkg_json: Dict[str, Any]) -> str:
    """The archive format the distribution uses for this package."""
    # Note that `split()` without arguments also copes with the handful of
    # PackageInfo.g files that separate the formats by more than one space.
    return pkg_json["ArchiveFormats"].split()[0]


def archive_name(pkg_name: str) -> str:
    pkg_json = metadata(pkg_name)
    return pkg_json["ArchiveURL"].split("/")[-1] + archive_format(pkg_json)


def archive_url(pkg_json: Dict[str, Any]) -> str:
    return pkg_json["ArchiveURL"] + archive_format(pkg_json)


# https://stackoverflow.com/questions/8299386/modifying-a-symlink-in-python/55742015#55742015
def symlink(target: str, link_name: str, overwrite: bool = False) -> None:
    """
    Create a symbolic link named link_name pointing to target.
    If link_name exists then FileExistsError is raised, unless overwrite=True.
    When trying to overwrite a directory, IsADirectoryError is raised.
    """

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
            raise IsADirectoryError(
                f"Cannot symlink over existing directory: '{link_name}'"
            )
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
        out, err = GAP.communicate(input=commands.encode("utf-8"))
        return GAP.returncode, out


def gap_exec2(commands: str, args: str = "") -> int:
    with subprocess.Popen(
        "gap -A -b --quitonbreak -q " + args,
        stdin=subprocess.PIPE,
        shell=True,
    ) as GAP:
        GAP.communicate(input=commands.encode("utf-8"))
        return GAP.returncode
