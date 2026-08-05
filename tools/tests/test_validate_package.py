# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, missing-function-docstring
# pylint: disable=missing-class-docstring, invalid-name, redefined-outer-name

"""
This module contains some tests for the validate_package.py script
"""

import os
import sys
from os.path import join

import pytest

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)

from validate_package import check_html_links, check_link

# Where a package manual usually keeps its chapters, and hence the vantage
# point from which most links are resolved.
CHAPTER = join("doc", "chap1.html")


@pytest.mark.parametrize(
    "href",
    [
        "https://www.gap-system.org/",
        "http://www.gap-system.org/",
        "mailto:support@gap-system.org",
        "#X7DC99E4284093FBB",
        "",
        "chap2.html",
        "chap2.html#X7DC99E4284093FBB",
        "../README.md",
        # A package manual reaches the GAP reference manual, and the manual of
        # another package, by climbing out of its own directory.
        "../../../doc/ref/chap37.html",
        "../../../pkg/gapdoc/doc/chap6.html",
    ],
)
def test_check_link_accepts(href):
    assert check_link(href, CHAPTER) is None


@pytest.mark.parametrize(
    "href",
    [
        # An absolute path only ever resolves on the machine that built the
        # documentation.
        "/Users/someone/gap/doc/ref/chap37.html",
        "/doc/ref/chap1.html",
        "//www.gap-system.org/doc",
        "C:\\gap\\doc\\ref.html",
        # Schemes we do not accept ...
        "file:///etc/passwd",
        "ftp://ftp.example.com/paper.dvi.gz",
        # ... including the marker that GAP's own etc/convert.pl leaves behind
        # for a cross reference it could not resolve.
        "badlink:ref:Matrix Groups in Characteristic 0",
        # Climbing further than <gaproot>.
        "../../../../../../etc/passwd",
    ],
)
def test_check_link_rejects(href):
    assert check_link(href, CHAPTER) is not None


def test_check_link_counts_from_the_file_that_contains_it():
    # The same link is fine from a chapter one level down, and leaves the GAP
    # installation from a file at the top of the package.
    assert check_link("../../../doc/ref/chap37.html", CHAPTER) is None
    assert check_link("../../../doc/ref/chap37.html", "index.html") is not None


def write_html(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<html><body>{body}</body></html>\n")


def test_check_html_links_accepts_a_clean_package(tmpdir):
    pkgdir = str(tmpdir)
    write_html(
        join(pkgdir, "doc", "chap1.html"),
        '<a href="chap2.html">next</a>'
        '<a href="../../../doc/ref/chap37.html">the reference manual</a>'
        '<a href="https://www.gap-system.org/">GAP</a>',
    )
    # Files that are not HTML are none of our business.
    with open(join(pkgdir, "PackageInfo.g"), "w", encoding="utf-8") as f:
        f.write('SetPackageInfo( rec( PackageName := "<a href=\\"/bad\\">" ) );\n')

    check_html_links(pkgdir, "testpkg")


def test_check_html_links_rejects_bad_links(tmpdir, capsys):
    pkgdir = str(tmpdir)
    write_html(join(pkgdir, "doc", "chap1.html"), '<a href="/etc/passwd">boom</a>')

    with pytest.raises(SystemExit) as e:
        check_html_links(pkgdir, "testpkg")
    assert e.value.code == 1

    # The author is told which file to look at, and where in it.
    reported = capsys.readouterr().err
    assert join("doc", "chap1.html") + ":1:" in reported
    assert "/etc/passwd" in reported


def test_check_html_links_searches_the_whole_package(tmpdir):
    # Documentation is not always below doc/: old style manuals live in htm/,
    # and some packages ship whole web pages alongside.
    pkgdir = str(tmpdir)
    write_html(join(pkgdir, "htm", "CHAP001.htm"), '<a href="badlink:ref:Foo">x</a>')

    with pytest.raises(SystemExit) as e:
        check_html_links(pkgdir, "testpkg")
    assert e.value.code == 1


def test_check_html_links_caps_the_number_it_reports(tmpdir, capsys):
    pkgdir = str(tmpdir)
    write_html(
        join(pkgdir, "doc", "chap1.html"),
        "".join(f'<a href="/bad/{i}">x</a>' for i in range(50)),
    )

    with pytest.raises(SystemExit):
        check_html_links(pkgdir, "testpkg")
    assert "and 30 more" in capsys.readouterr().err
