# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, missing-function-docstring
# pylint: disable=missing-class-docstring, invalid-name, redefined-outer-name

"""
This module contains some tests for the download_packages.py script
"""

import os
import runpy
import shutil
import sys
from os.path import exists, join

import mock
import pytest
from requests import RequestException

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)


from download_packages import download_archive, main

# TODO: move the tests for these functions to their own test file?
from utils import archive_name, archive_url, metadata


@pytest.fixture
def ensure_in_tests_dir():
    os.chdir(os.path.dirname(os.path.realpath(__file__)))


@pytest.fixture
def test_metadata(ensure_in_tests_dir):
    meta = metadata("aclib")
    assert (
        meta["ArchiveSHA256"]
        == "f672d0aee19f22b411352835a4730a6f88eecad7d79d8452b273f381b03e1a7b"
    )
    assert meta["PackageName"] == "AClib"
    assert (
        meta["Persons"][1]["PostalAddress"]
        == "Institut Analysis und Algebra\nTU Braunschweig\nUniversitätsplatz 2\nD-38106 Braunschweig\nGermany"
    )

    # Non-existent file
    with pytest.raises(SystemExit) as e:
        meta = metadata("bananas")
    assert e.type == SystemExit
    assert e.value.code == 1

    # Bad json
    with pytest.raises(SystemExit) as e:
        meta = metadata("badjson")
    assert e.type == SystemExit
    assert e.value.code == 1


def test_archive_name(ensure_in_tests_dir):
    assert archive_name("aclib") == "aclib-1.3.2.tar.gz"

    # Non-existent file
    with pytest.raises(SystemExit) as e:
        meta = archive_name("bananas")
    assert e.type == SystemExit
    assert e.value.code == 1

    # Bad json
    with pytest.raises(SystemExit) as e:
        meta = archive_name("badjson")
    assert e.type == SystemExit
    assert e.value.code == 1


def test_archive_url():
    #     assert (
    #         archive_url(metadata("aclib"))
    #         == "https://github.com/gap-packages/aclib/releases/download/v1.3.2/aclib-1.3.2.tar.gz"
    #     )

    # Non-existent file
    with pytest.raises(SystemExit) as e:
        meta = archive_url(metadata("bananas"))
    assert e.type == SystemExit
    assert e.value.code == 1

    # Bad json
    with pytest.raises(SystemExit) as e:
        meta = archive_url(metadata("badjson"))
    assert e.type == SystemExit
    assert e.value.code == 1


def test_download_archive(ensure_in_tests_dir, tmpdir):
    with mock.patch(
        "requests.get", side_effect=RequestException("Failed Request")
    ) as mock_request_post:
        with pytest.raises(RequestException) as e:
            download_archive(str(tmpdir), "unipot")
        assert e.type == RequestException

    download_archive(str(tmpdir), "aclib")
    assert exists(join(str(tmpdir), archive_name("aclib")))

    download_archive(str(tmpdir), "unipot")
    assert exists(join(str(tmpdir), archive_name("unipot")))

    download_archive(str(tmpdir), "unipot")
    assert exists(join(str(tmpdir), archive_name("unipot")))

    with pytest.raises(SystemExit) as e:
        download_archive(str(tmpdir), "notapackagename")
    assert e.type == SystemExit
    assert e.value.code == 1


def test_main(ensure_in_tests_dir):
    main(["unipot", "aclib"])
    shutil.rmtree("_archives")
