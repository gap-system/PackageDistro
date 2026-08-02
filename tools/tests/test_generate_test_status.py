# -*- coding: utf-8 -*-
# pylint: disable=missing-function-docstring, invalid-name

import importlib
import os
import sys

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)


def test_github_headers_use_bearer_token():
    module = importlib.import_module("generate_test_status")

    assert module.github_headers("secret-token") == {
        "Authorization": "Bearer secret-token"
    }


def test_report_id_splits_date_into_year_and_month_directories():
    module = importlib.import_module("generate_test_status")

    assert (
        module.report_id("master", "2026-08-02 13:39:15")
        == "master/2026/08/02_13-39-15"
    )


def test_report_id_contains_no_colons():
    module = importlib.import_module("generate_test_status")

    assert ":" not in module.report_id("master", "2026-08-02 13:39:15")


def test_report_id_prefixes_synthetic_pr_keys_unchanged():
    module = importlib.import_module("generate_test_status")

    assert (
        module.report_id("pr-gap-system-gap-1234-01234567", "2026-12-31 00:00:00")
        == "pr-gap-system-gap-1234-01234567/2026/12/31_00-00-00"
    )


def test_fetch_jobs_returns_empty_list_for_error_payload():
    module = importlib.import_module("generate_test_status")
    seen = {}

    class Response:
        links = {}

        def raise_for_status(self):
            return None

        def json(self):
            return {"message": "Bad credentials"}

    def fake_get(url, headers):
        seen["url"] = url
        seen["headers"] = headers
        return Response()

    assert module.fetch_jobs("TOKEN", "gap-system/PackageDistro", "123", fake_get) == []
    assert "filter=all" in seen["url"]
    assert seen["headers"] == {"Authorization": "Bearer TOKEN"}
