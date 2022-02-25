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

import pytest

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)

from scan_for_updates import (
    download_pkg_info,
    gap_exec,
    main,
    output_json,
    scan_for_one_update,
    scan_for_updates,
    sha256,
    skip,
)


@pytest.fixture
def ensure_in_tests_dir():
    os.chdir(os.path.dirname(os.path.realpath(__file__)))


def reset():
    os.system("git checkout -- badjson/meta.json")
    os.system("git checkout -- aclib/meta.json")
    os.system("git checkout -- atlasrep/meta.json")
    if exists("_pkginfos"):
        shutil.rmtree("_pkginfos")
    if exists("_archives"):
        shutil.rmtree("_archives")
    if exists(".fakefile"):
        os.remove(".fakefile")


def test_skip():
    assert skip(".DS_STORE")
    assert skip("__file__")
    assert skip("README.md")
    assert not skip("digraphs")


def test_sha256(ensure_in_tests_dir):
    assert (
        sha256("_data/digraphs.g")
        == "95a109df953e22dfd07c382ef0f7927dfea90e1b1ce40d59178ed8c045a3fb72"
    )
    assert (
        sha256("_data/digraphs.g.gz")
        == "fc16a80831f4a7d3699f073ed8a5cb789b1ee9586eae3d4b76801c7e36d21749"
    )


def test_download_pkg_info(ensure_in_tests_dir):
    assert download_pkg_info("aclib")

    with pytest.raises(SystemExit) as e:
        download_pkg_info("badjson")
    assert e.type == SystemExit
    assert e.value.code == 1

    # Intentionally messed up the url field
    assert not download_pkg_info("toricvarieties")


def test_exec_gap(ensure_in_tests_dir):
    if shutil.which("gap") == None:
        return
    assert gap_exec("FORCE_QUIT_GAP(0);") == 0
    assert gap_exec("FORCE_QUIT_GAP(1);") == 1


def test_scan_for_one_update(ensure_in_tests_dir, tmpdir):
    scan_for_one_update(str(tmpdir), "aclib")
    assert exists(join(str(tmpdir), "aclib.g"))
    scan_for_one_update(str(tmpdir), "toricvarieties")
    assert not exists(join(str(tmpdir), "toricvarieties.g"))
    scan_for_one_update(str(tmpdir), "atlasrep")
    assert exists(join(str(tmpdir), "atlasrep.g"))

    os.system("git checkout -- aclib/meta.json")
    os.system("git checkout -- atlasrep/meta.json")


def test_scan_updates(ensure_in_tests_dir, tmpdir):
    if shutil.which("gap") == None:
        return
    with pytest.raises(SystemExit) as e:
        scan_for_updates(str(tmpdir))
    # fails because badjson is considered and bad!
    assert e.type == SystemExit
    assert e.value.code == 1

    output_json(str(tmpdir))
    assert os.system("git diff --exit-code aclib/meta.json") != 0
    assert os.system("git diff --exit-code atlasrep/meta.json") != 0
    assert os.system("git diff --exit-code badjson/meta.json") == 0
    assert os.system("git diff --exit-code toricvarieties/meta.json") == 0
    reset()
    output_json("bananaananan")


def test_main(ensure_in_tests_dir):
    if shutil.which("gap") == None:
        return
    shutil.rmtree("badjson")
    os.mkdir("_pkginfos")
    os.system("touch _pkginfos/.fakefile")
    main()
    reset()


def test_main_again(ensure_in_tests_dir):
    if shutil.which("gap") == None:
        return
    shutil.rmtree("badjson")
    main()
    reset()
