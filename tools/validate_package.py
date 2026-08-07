#!/usr/bin/env python3

#############################################################################
##
##  This file is part of GAP, a system for computational discrete algebra.
##
##  Copyright of GAP belongs to its developers, whose names are too numerous
##  to list here. Please refer to the COPYRIGHT file for details.
##
##  SPDX-License-Identifier: GPL-2.0-or-later
##

# pylint: disable=C0116, C0103

"""
Runs some basic validation of the pkgname/meta.json against the package
archive, and the old meta data.

Should be run after scan_for_updates.py. Arguments can be either a package
name, or the path to a meta.json file. For example:

    $ tools/validate_package.py aclib
    _archives/aclib-1.3.3.tar.gz already exists, not downloading again
    aclib: PASSED
    $ tools/validate_package.py walrus/meta.json
    _archives/walrus-0.9991.tar.gz already exists, not downloading again
    walrus: PASSED
"""

import os
import sys
import tarfile
import urllib.parse
from html.parser import HTMLParser
from os.path import join
from tempfile import TemporaryDirectory
from typing import List, Optional, Tuple

import utils
from download_packages import download_archive
from utils import (
    archive_name,
    download_to_memory,
    error,
    metadata,
    normalize_pkg_name,
    notice,
    sha256,
    warning,
)


def validate_tarball(filename: str) -> str:
    with tarfile.open(filename) as tf:
        names = tf.getnames()
        if len(names) == 0:
            error("tarball is empty")

        # no entry may contain ".."
        first = next(filter(lambda n: ".." in n, names), None)
        if first != None:
            error(f"tarball has bad entry {first}")

        # get the basedir (all entries are supposed to be contained in that)
        basedir = names[0].split("/")[0]

        # all entries must either be equal to basedir or start with basedir+'/'
        badentries = filter(lambda n: basedir != n.split("/")[0], names)
        first = next(badentries, None)
        if first != None:
            error(f"tarball has entry {first} outside of basedir {basedir}")

        # must have a PackageInfo.g
        if not os.path.join(basedir, "PackageInfo.g") in names:
            error("tarball is missing PackageInfo.g")

        # must not contain symlinks (these often cause trouble on Windows).
        # TODO: if anyone ever really needs symlinks, then at the very least
        # we should prevent symlinks pointing outside the package directory.
        symlinks = [x for x in tf.getnames() if tf.getmember(x).issym()]
        if len(symlinks) > 0:
            error(f"tarball contains symlinks: {symlinks}")

        return basedir


HTML_SUFFIXES = (".html", ".htm", ".xhtml")

# The only URL schemes a link in package documentation may use. Anything else
# is either unusable offline (`file:`), no longer something we want to send
# readers to (`ftp:`), or not a scheme at all but a marker left behind by a
# documentation tool: GAP's own `etc/convert.pl` turns a cross reference it
# cannot resolve into `badlink:...`.
ALLOWED_SCHEMES = ("http", "https", "mailto")

# Package documentation is installed at `<gaproot>/pkg/<name>/`, so a relative
# link may climb two levels above the package directory -- that is how a manual
# links into the GAP reference manual, or into another package -- but no
# further, as that would leave the GAP installation altogether.
GAPROOT_HEADROOM = 2

# A package with a systematic problem produces one complaint per link, of which
# a handful tell the author everything they need to know.
MAX_REPORTED_LINKS = 20


class LinkExtractor(HTMLParser):
    """Collects the target of every `<a href="...">` along with its line."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: List[Tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value is not None:
                self.links.append((self.getpos()[0], value))


def check_link(href: str, relpath: str) -> Optional[str]:
    """Say what is wrong with the link `href`, or None if it is acceptable.

    `relpath` is the path of the HTML file containing the link, relative to
    the package directory; it decides how far up a relative link reaches.

    Only links that are wrong wherever the package is installed are rejected.
    Whether a relative link points at a file that actually exists is
    deliberately not checked: some packages generate parts of their
    documentation only after installation, so that check needs to be
    introduced more carefully.
    """
    href = href.strip()
    if not href or href.startswith("#"):
        return None

    parsed = urllib.parse.urlparse(href)
    if parsed.scheme:
        if parsed.scheme in ALLOWED_SCHEMES:
            return None
        if len(parsed.scheme) == 1:
            # A Windows drive letter, e.g. "C:\gap\doc\ref.html".
            return f"absolute path: {href}"
        return f"URL scheme {parsed.scheme}: is not allowed: {href}"
    if href.startswith("/"):
        # Both "/doc/ref" and the protocol relative "//host/doc" only ever
        # resolve to something outside the GAP installation.
        return f"absolute path: {href}"

    target = urllib.parse.unquote(parsed.path)
    if not target:
        return None
    resolved = os.path.normpath(os.path.join(os.path.dirname(relpath), target))
    up = 0
    for part in resolved.split(os.sep):
        if part != "..":
            break
        up += 1
    if up > GAPROOT_HEADROOM:
        return f"link leaves the GAP installation: {href}"
    return None


def check_html_links(pkgdir: str, pkg_name: str) -> None:
    """Check the links in all HTML files shipped by a package."""
    problems = []
    for dirpath, dirnames, filenames in os.walk(pkgdir):
        dirnames.sort()
        for name in sorted(filenames):
            if not name.lower().endswith(HTML_SUFFIXES):
                continue
            path = join(dirpath, name)
            relpath = os.path.relpath(path, pkgdir)
            with open(path, "rb") as f:
                # Package documentation is not always valid UTF-8, and a byte
                # we cannot decode is no reason to reject a package; it cannot
                # be part of a link we would complain about either.
                text = f.read().decode("utf-8", errors="replace")
            parser = LinkExtractor()
            parser.feed(text)
            for line, href in parser.links:
                reason = check_link(href, relpath)
                if reason is not None:
                    problems.append(f"{relpath}:{line}: {reason}")

    if problems:
        shown = problems[:MAX_REPORTED_LINKS]
        if len(problems) > len(shown):
            shown.append(f"... and {len(problems) - len(shown)} more")
        details = "\n  ".join(shown)
        error(f"{pkg_name}: bad links in HTML documentation:\n  {details}")


def validate_package(archive_fname: str, pkgdir: str, pkg_name: str) -> None:
    pkg_json = metadata(pkg_name)

    # validate PackageInfoURL (download_to_memory raises an exception if download fails)
    data = download_to_memory(pkg_json["PackageInfoURL"])
    # We deliberately do not compare the SHA256 of `data` against PackageInfoSHA256
    # as it may be that a different version of the package was released in the meantime

    # validate README_URL (download_to_memory raises an exception if download fails)
    data = download_to_memory(pkg_json["README_URL"])
    # We could compare the SHA256 of `data` against the README in the package archive,
    # but this is really unimportant, so it's simpler for everyone to just let mistakes
    # here slide (there is an argument to be made that we should just drop README_URL
    # completely anyway)

    # verify the SHA256 for the PackageInfo.g that we recorded as PackageInfoSHA256
    # matches what is in the tarball
    pkg_info_name = join(pkgdir, "PackageInfo.g")
    if pkg_json["PackageInfoSHA256"] != sha256(pkg_info_name):
        error(f"{pkg_name}: PackageInfoSHA256 is not the SHA256 of {pkg_info_name}")

    # verify the SHA256 for archive that we recorded as ArchiveSHA256
    if pkg_json["ArchiveSHA256"] != sha256(archive_fname):
        error(f"{pkg_name}: ArchiveSHA256 is not the SHA256 of {archive_fname}")

    # `scan_for_updates.py` stores the release date in ISO format; catch
    # hand-edited metadata that reverts to the traditional DD/MM/YYYY, or that
    # contains a date we cannot make sense of at all
    try:
        iso_date = utils.normalize_date(pkg_json["Date"])
    except ValueError as e:
        error(f"{pkg_name}: {e}")
    if pkg_json["Date"] != iso_date:
        error(f"{pkg_name}: Date {pkg_json['Date']} is not in YYYY-MM-DD format")

    check_html_links(pkgdir, pkg_name)


def main(pkgs: List[str]) -> None:
    archive_dir = "_archives"
    dir_of_this_file = os.path.dirname(os.path.realpath(__file__))

    with TemporaryDirectory() as tempdir:
        for pkg_name in pkgs:
            try:
                archive_fname = download_archive(archive_dir, pkg_name)
                pkgdir = join(tempdir, validate_tarball(archive_fname))
                utils.unpack_archive(archive_fname, tempdir)
                validate_package(archive_fname, pkgdir, pkg_name)
                result = utils.gap_exec2(
                    f'ValidatePackagesArchive("{pkgdir}", "{pkg_name}");',
                    args=f"{dir_of_this_file}/validate_package.g",
                )
                if result != 0:
                    error(f"{pkg_name}: FAILED: ValidatePackagesArchive failed")
            except Exception as e:
                error(f"{pkg_name}: FAILED: {e}")
            notice(f"{pkg_name}: PASSED")


if __name__ == "__main__":
    main([normalize_pkg_name(x) for x in sys.argv[1:]])
