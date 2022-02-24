# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, missing-function-docstring
# pylint: disable=missing-class-docstring, invalid-name, redefined-outer-name

"""
This module contains some tests for the scan_for_updates.py script
"""
import json
import os
import sys

import pytest

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)
from scan_for_updates import metadata, sha256, skip, download_archive


def test_skip():
    assert skip(".DS_STORE")
    assert skip("__file__")
    assert skip("README.md")
    assert not skip("digraphs")


def test_sha256():
    assert (
        sha256("tests/digraphs.g")
        == "95a109df953e22dfd07c382ef0f7927dfea90e1b1ce40d59178ed8c045a3fb72"
    )
    assert (
        sha256("tests/digraphs.g.gz")
        == "fc16a80831f4a7d3699f073ed8a5cb789b1ee9586eae3d4b76801c7e36d21749"
    )


def test_metadata():
    meta = metadata("tests")
    assert (
        meta["ArchiveSHA256"]
        == "f672d0aee19f22b411352835a4730a6f88eecad7d79d8452b273f381b03e1a7b"
    )
    assert meta["PackageName"] == "AClib"
    assert (
        meta["Persons"][1]["PostalAddress"]
        == "Institut Analysis und Algebra\nTU Braunschweig\nUniversitätsplatz 2\nD-38106 Braunschweig\nGermany"
    )

    with pytest.raises(SystemExit) as e:
        meta = metadata("bananas")
    assert e.type == SystemExit
    assert e.value.code == 1

    with pytest.raises(SystemExit) as e:
        meta = metadata("tests/data1")
    assert e.type == SystemExit
    assert e.value.code == 1


def test_download_archive():
    meta = metadata("tests")
    url = meta["ArchiveURL"] + meta["ArchiveFormats"].split(" ")[0]
    download_archive("aclib", url, "tests/test-archive.tar.gz")
    with pytest.raises(AssertionError) as e:
        download_archive("bananas", "not a url", "doesn't end in zip")

    with pytest.raises(SystemExit) as e:
        download_archive("bananas", "not a url", "bananas.zip")
    assert e.type == SystemExit
    assert e.value.code == 1

    download_archive(
        "bananas", "archive already exists", "tests/test-archive.tar.gz"
    )

    os.remove("tests/test-archive.tar.gz")
