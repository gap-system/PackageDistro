# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)

from prepare_pr import automerge_notice, body_for_packages, infostr_for_package


def test_infostr_for_package_includes_archive_size():
    pkg_json = {
        "ArchiveFormats": ".tar.gz",
        "ArchiveSize": 12939427,
        "ArchiveURL": "https://example.com/testpkg-1.0",
        "PackageInfoURL": "https://example.com/PackageInfo.g",
        "PackageName": "TestPkg",
        "PackageWWWHome": "https://example.com",
        "README_URL": "https://example.com/README",
        "Version": "1.0",
    }

    info = infostr_for_package(pkg_json)

    assert (
        "[[source archive](https://example.com/testpkg-1.0.tar.gz) (12.9 MB)]" in info
    )


def test_body_for_packages_mentions_maintainers_with_github_usernames():
    pkg_json = {
        "ArchiveFormats": ".tar.gz",
        "ArchiveSize": 12939427,
        "ArchiveURL": "https://example.com/testpkg-1.0",
        "IssueTrackerURL": "https://example.com/issues",
        "PackageInfoURL": "https://example.com/PackageInfo.g",
        "PackageName": "TestPkg",
        "PackageWWWHome": "https://example.com",
        "README_URL": "https://example.com/README",
        "SourceRepository": {"URL": "https://example.com/repo"},
        "Version": "1.0",
        "Persons": [
            {
                "FirstNames": "Maint",
                "GitHubUsername": "maintainer",
                "IsMaintainer": True,
            },
            {
                "FirstNames": "Author",
                "GitHubUsername": "author",
                "IsMaintainer": False,
            },
            {
                "FirstNames": "No Handle",
                "IsMaintainer": True,
            },
        ],
    }

    body = body_for_packages([pkg_json])

    assert "Maintainers: @maintainer" in body
    assert "@author" not in body


def test_automerge_notice_mentions_blocking_comments():
    notice = automerge_notice()

    assert "prevent this pull request from being auto-merged" in notice
    assert "[noblock]" in notice
