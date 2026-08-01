# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, missing-function-docstring
# pylint: disable=missing-class-docstring, invalid-name, redefined-outer-name

"""
This module contains some tests for the helpers in utils.py
"""

import glob
import json
import os
import sys
from os.path import join

import pytest

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)

from utils import normalize_date


def test_normalize_date():
    # The traditional GAP format is converted...
    assert normalize_date("28/08/2025") == "2025-08-28"
    assert normalize_date("01/12/1999") == "1999-12-01"

    # ...and a date that is already in ISO format is left alone.
    assert normalize_date("2025-08-28") == "2025-08-28"

    # A day and month that could be read either way is still DD/MM/YYYY.
    assert normalize_date("05/09/2025") == "2025-09-05"


def test_normalize_date_rejects_bad_dates():
    for date in [
        "",
        "2025-08-28 ",
        "28.08.2025",
        "2025/08/28",  # YYYY/MM/DD is neither of the two accepted formats
        "08/28/2025",  # month and day the American way round
        "31/02/2025",  # not a real date
        "2025-02-31",
    ]:
        with pytest.raises(SystemExit) as e:
            normalize_date(date)
        assert e.value.code == 1, date


def test_distributed_metadata_uses_iso_dates():
    # Guard against a hand-edited meta.json reintroducing the DD/MM/YYYY dates
    # we used to copy verbatim out of PackageInfo.g: consumers of the metadata
    # should be able to rely on a single format.
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    metas = sorted(glob.glob(join(root, "packages", "*", "meta.json")))
    assert metas, "found no packages to check"
    for fname in metas:
        with open(fname, "r", encoding="utf-8") as f:
            date = json.load(f)["Date"]
        assert date == normalize_date(date), fname
