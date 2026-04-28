# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, missing-function-docstring
# pylint: disable=missing-class-docstring, invalid-name, redefined-outer-name

"""
This module contains some tests for the scan_for_updates.py script
"""

import json
import os
import shutil
import sys
from os.path import exists, join

import mock
import pytest
import requests

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)

from scan_for_updates import (
    import_packages,
    main,
    scan_for_one_update,
    scan_for_updates,
)
from utils import download_to_memory, gap_exec, metadata, sha256


@pytest.fixture
def ensure_in_tests_dir():
    os.chdir(os.path.dirname(os.path.realpath(__file__)))


def reset():
    os.system("git checkout -- packages/badjson/meta.json")
    os.system("git checkout -- packages/aclib/meta.json")
    os.system("git checkout -- packages/atlasrep/meta.json")
    if exists("_pkginfos"):
        shutil.rmtree("_pkginfos")
    if exists("_archives"):
        shutil.rmtree("_archives")
    if exists(".fakefile"):
        os.remove(".fakefile")


def test_sha256(ensure_in_tests_dir):
    assert (
        sha256("_data/digraphs.g")
        == "95a109df953e22dfd07c382ef0f7927dfea90e1b1ce40d59178ed8c045a3fb72"
    )
    assert (
        sha256("_data/digraphs.g.gz")
        == "fc16a80831f4a7d3699f073ed8a5cb789b1ee9586eae3d4b76801c7e36d21749"
    )


def test_download_to_memory(ensure_in_tests_dir):
    assert download_to_memory("https://gap-packages.github.io/aclib/PackageInfo.g")

    with pytest.raises(requests.HTTPError) as e:
        download_to_memory("https://gap-packages.github.io/BADURL.bad.bad")
    assert e.type == requests.HTTPError
    assert e.value.response.status_code == 404


def test_exec_gap(ensure_in_tests_dir):
    if shutil.which("gap") == None:
        return
    assert gap_exec("FORCE_QUIT_GAP(0);") == (0, b"")
    assert gap_exec("FORCE_QUIT_GAP(1);") == (1, b"")


def test_scan_for_one_update(ensure_in_tests_dir, tmpdir):
    scan_for_one_update(str(tmpdir), "aclib")
    assert exists(join(str(tmpdir), "aclib.g"))
    scan_for_one_update(str(tmpdir), "atlasrep")
    assert exists(join(str(tmpdir), "atlasrep.g"))

    os.system("git checkout -- packages/aclib/meta.json")
    os.system("git checkout -- packages/atlasrep/meta.json")


def test_scan_updates(ensure_in_tests_dir, tmpdir):
    if shutil.which("gap") == None:
        return
    with pytest.raises(SystemExit) as e:
        scan_for_updates(str(tmpdir), True)
    # fails because badjson is considered and bad!
    assert e.type == SystemExit
    assert e.value.code == 1
    reset()


def test_main(ensure_in_tests_dir):
    if shutil.which("gap") == None:
        return
    shutil.rmtree("packages/badjson")
    os.mkdir("_pkginfos")
    os.system("touch _pkginfos/.fakefile")
    main()
    reset()


def test_main_again(ensure_in_tests_dir):
    if shutil.which("gap") == None:
        return
    shutil.rmtree("packages/badjson")
    main()
    reset()


def test_import_packages_records_archive_size(ensure_in_tests_dir, tmpdir):
    pkg_json = {
        "ArchiveFormats": ".tar.gz",
        "ArchiveURL": "https://example.com/testpkg-1.0",
        "PackageName": "TestPkg",
        "Version": "1.0",
    }
    archive_bytes = b"archive-bytes-go-here"

    def fake_download(_url, dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(archive_bytes)

    with mock.patch(
        "scan_for_updates.parse_pkginfo_files", return_value=[pkg_json]
    ), mock.patch("scan_for_updates.utils.download", side_effect=fake_download):
        import_packages(["dummy.g"])

    meta = metadata("testpkg")
    archive_path = "_archives/testpkg-1.0.tar.gz"
    assert meta["ArchiveSHA256"] == sha256(archive_path)
    assert meta["ArchiveSize"] == len(archive_bytes)

    shutil.rmtree("packages/testpkg")
    shutil.rmtree("_archives")
