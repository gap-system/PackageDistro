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
import requests
from requests import RequestException

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)


from download_packages import ChecksumError, download_archive, main

# TODO: move the tests for these functions to their own test file?
from utils import _should_retry, archive_name, archive_url, download, metadata


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


# The "goodsha" and "badsha" test packages exist so that the checksum handling
# can be exercised without network access: `fake_download` always writes
# FAKE_ARCHIVE, which matches the checksum recorded for "goodsha" but not the
# one recorded for "badsha".
FAKE_ARCHIVE = b"test archive contents\n"


def fake_download(url, dst):
    with open(dst, "wb") as f:
        f.write(FAKE_ARCHIVE)


def test_download_archive_verifies_checksum(ensure_in_tests_dir, tmpdir):
    with mock.patch("download_packages.download", side_effect=fake_download):
        fname = download_archive(str(tmpdir), "goodsha")
    assert exists(fname)
    assert not exists(fname + ".part")
    with open(fname, "rb") as f:
        assert f.read() == FAKE_ARCHIVE


def test_download_archive_bad_checksum(ensure_in_tests_dir, tmpdir):
    archive_fname = join(str(tmpdir), archive_name("badsha"))

    # A pre-existing, good archive must survive a failed re-download.
    with open(archive_fname, "wb") as f:
        f.write(b"previous contents")

    with mock.patch("download_packages.download", side_effect=fake_download):
        with pytest.raises(ChecksumError):
            download_archive(str(tmpdir), "badsha")

    # No partial download is left behind, and the old archive is untouched.
    assert not exists(archive_fname + ".part")
    with open(archive_fname, "rb") as f:
        assert f.read() == b"previous contents"


def test_download_archive_removes_part_file_on_error(ensure_in_tests_dir, tmpdir):
    with mock.patch(
        "download_packages.download", side_effect=RequestException("Failed Request")
    ):
        with pytest.raises(RequestException):
            download_archive(str(tmpdir), "goodsha")
    assert not exists(join(str(tmpdir), archive_name("goodsha") + ".part"))
    assert not exists(join(str(tmpdir), archive_name("goodsha")))


def http_error(status_code):
    response = mock.Mock()
    response.status_code = status_code
    return requests.HTTPError(response=response)


def ok_response(content=FAKE_ARCHIVE):
    response = mock.Mock()
    response.raise_for_status.return_value = None
    response.raw.stream.return_value = iter([content])
    return response


def test_should_retry():
    # Transient: worth another attempt.
    assert _should_retry(requests.ConnectionError())
    assert _should_retry(requests.Timeout())
    assert _should_retry(http_error(429))
    assert _should_retry(http_error(503))

    # Permanent: retrying would only waste time.
    assert not _should_retry(http_error(404))
    assert not _should_retry(http_error(401))
    assert not _should_retry(RequestException("Failed Request"))


def test_download_retries_transient_failures(tmpdir):
    dst = join(str(tmpdir), "archive.tar.gz")
    responses = [requests.ConnectionError(), http_error(503), ok_response()]
    with mock.patch("time.sleep"):  # do not actually wait between attempts
        with mock.patch("requests.get", side_effect=responses) as get:
            download("https://example.com/archive.tar.gz", dst)
    assert get.call_count == 3
    with open(dst, "rb") as f:
        assert f.read() == FAKE_ARCHIVE


def test_download_does_not_retry_permanent_failures(tmpdir):
    dst = join(str(tmpdir), "archive.tar.gz")
    with mock.patch("time.sleep"):
        with mock.patch("requests.get", side_effect=http_error(404)) as get:
            with pytest.raises(requests.HTTPError):
                download("https://example.com/archive.tar.gz", dst)
    assert get.call_count == 1


def test_main_continues_after_failure(ensure_in_tests_dir, tmpdir):
    # A failing package must not stop the ones listed after it.
    with mock.patch("download_packages.download", side_effect=fake_download):
        with pytest.raises(SystemExit) as e:
            main(["badsha", "goodsha", "--archive-dir", str(tmpdir)])
    assert e.value.code == 1

    assert not exists(join(str(tmpdir), archive_name("badsha")))
    assert exists(join(str(tmpdir), archive_name("goodsha")))
