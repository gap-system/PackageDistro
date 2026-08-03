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
    local_pkginfo,
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
    try:
        with pytest.raises(SystemExit) as e:
            # fails because badjson is considered and bad!
            scan_for_updates(["aclib", "badjson"], str(tmpdir), True)
        assert e.type == SystemExit
        assert e.value.code == 1
    finally:
        reset()


def test_main(ensure_in_tests_dir):
    if shutil.which("gap") == None:
        return
    # a leftover _pkginfos directory must not upset the scan
    os.mkdir("_pkginfos")
    os.system("touch _pkginfos/.fakefile")
    try:
        main(["aclib"])
    finally:
        reset()


def test_main_again(ensure_in_tests_dir):
    if shutil.which("gap") == None:
        return
    try:
        main(["aclib"])
    finally:
        reset()


@pytest.fixture
def local_pkg(tmpdir):
    """A directory holding a PackageInfo.g, as an unreleased package would."""
    pkgdir = join(str(tmpdir), "my_gap_package")
    os.mkdir(pkgdir)
    pkginfo = join(pkgdir, "PackageInfo.g")
    with open(pkginfo, "w", encoding="utf-8") as f:
        f.write('SetPackageInfo( rec( PackageName := "MyGapPackage" ) );\n')
    return pkgdir, pkginfo


def test_local_pkginfo_accepts_directory_or_file(ensure_in_tests_dir, local_pkg):
    pkgdir, pkginfo = local_pkg

    assert local_pkginfo(pkgdir) == pkginfo
    assert local_pkginfo(pkginfo) == pkginfo


def test_local_pkginfo_leaves_package_names_alone(ensure_in_tests_dir):
    # These name a package of the distribution; the latter two are paths on
    # disk as well, and must not be mistaken for a local package.
    assert local_pkginfo("aclib") is None
    assert local_pkginfo("packages/aclib") is None
    assert local_pkginfo("packages/aclib/meta.json") is None


def test_local_pkginfo_rejects_directory_without_pkginfo(ensure_in_tests_dir, tmpdir):
    with pytest.raises(SystemExit) as e:
        local_pkginfo(str(tmpdir))
    assert e.value.code == 1


def test_local_pkginfo_rejects_nonexistent_path(ensure_in_tests_dir, tmpdir):
    with pytest.raises(SystemExit) as e:
        local_pkginfo(join(str(tmpdir), "no", "such", "package"))
    assert e.value.code == 1


def test_main_imports_local_package_without_scanning(ensure_in_tests_dir, local_pkg):
    pkgdir, pkginfo = local_pkg

    with mock.patch("scan_for_updates.import_packages") as fake_import, mock.patch(
        "scan_for_updates.scan_for_updates"
    ) as fake_scan:
        main([pkgdir])

    # The whole point: nothing is downloaded, the local file is imported as is.
    fake_scan.assert_not_called()
    fake_import.assert_called_once_with([pkginfo])


def test_main_rejects_mixing_names_and_paths(ensure_in_tests_dir, local_pkg):
    pkgdir, _ = local_pkg

    with pytest.raises(SystemExit) as e:
        main([pkgdir, "aclib"])
    assert e.value.code == 1


def test_import_packages_records_archive_size(ensure_in_tests_dir, tmpdir):
    pkg_json = {
        "ArchiveFormats": ".tar.gz",
        "ArchiveURL": "https://example.com/testpkg-1.0",
        "Date": "28/08/2025",
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
    # the DD/MM/YYYY date from the PackageInfo.g is stored in ISO format
    assert meta["Date"] == "2025-08-28"

    shutil.rmtree("packages/testpkg")
    shutil.rmtree("_archives")


def test_import_packages_skips_unparseable_dates(ensure_in_tests_dir, tmpdir):
    # A PackageInfo.g whose Date we cannot parse is skipped -- but only that
    # one package: everything else in the same batch is imported as usual.
    bad_pkg_json = {
        "ArchiveFormats": ".tar.gz",
        "ArchiveURL": "https://example.com/baddatepkg-1.0",
        "Date": "07/20/2026",  # month and day the American way round
        "PackageName": "BadDatePkg",
        "Version": "1.0",
    }
    good_pkg_json = {
        "ArchiveFormats": ".tar.gz",
        "ArchiveURL": "https://example.com/gooddatepkg-1.0",
        "Date": "20/07/2026",
        "PackageName": "GoodDatePkg",
        "Version": "1.0",
    }

    def fake_download(_url, dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(b"archive-bytes-go-here")

    try:
        with mock.patch(
            "scan_for_updates.parse_pkginfo_files",
            return_value=[bad_pkg_json, good_pkg_json],
        ), mock.patch("scan_for_updates.utils.download", side_effect=fake_download):
            import_packages(["bad.g", "good.g"])

        assert not exists("packages/baddatepkg")
        assert metadata("gooddatepkg")["Date"] == "2026-07-20"
    finally:
        shutil.rmtree("packages/baddatepkg", ignore_errors=True)
        shutil.rmtree("packages/gooddatepkg", ignore_errors=True)
        shutil.rmtree("_archives", ignore_errors=True)
