# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)

from prepare_pr import infostr_for_package


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
