# -*- coding: utf-8 -*-
# pylint: disable=missing-function-docstring, invalid-name

import importlib
import os
import sys

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)


def test_parse_gap_pull_request_url_accepts_standard_urls():
    module = importlib.import_module("gap_pr_utils")

    assert module.parse_gap_pull_request_url(
        "https://github.com/gap-system/gap/pull/1234"
    ) == ("gap-system", "gap", 1234)
    assert module.parse_gap_pull_request_url(
        "https://github.com/gap-system/gap/pull/1234/"
    ) == ("gap-system", "gap", 1234)
    assert module.parse_gap_pull_request_url(
        "https://github.com/gap-system/gap/pull/1234/files?foo=bar"
    ) == ("gap-system", "gap", 1234)


def test_parse_gap_pull_request_url_rejects_invalid_urls():
    module = importlib.import_module("gap_pr_utils")

    for bad_url in [
        "https://github.com/gap-system/gap/issues/1234",
        "https://github.com/gap-system/PackageDistro/pull/1234",
        "https://example.com/gap-system/gap/pull/1234",
        "not a url",
    ]:
        try:
            module.parse_gap_pull_request_url(bad_url)
        except ValueError as exc:
            assert "GAP pull request URL" in str(exc)
        else:
            raise AssertionError(f"expected ValueError for {bad_url}")


def test_resolve_gap_pull_request_normalizes_metadata():
    module = importlib.import_module("gap_pr_utils")

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "title": "Fix something",
                "base": {
                    "ref": "master",
                    "repo": {
                        "full_name": "gap-system/gap",
                        "clone_url": "https://github.com/gap-system/gap.git",
                    },
                },
                "head": {
                    "ref": "feature/test-pr",
                    "sha": "0123456789abcdef0123456789abcdef01234567",
                    "repo": {
                        "full_name": "contrib/gap",
                        "clone_url": "https://github.com/contrib/gap.git",
                        "html_url": "https://github.com/contrib/gap",
                    },
                },
            }

    seen = {}

    def fake_get(url, headers):
        seen["url"] = url
        seen["headers"] = headers
        return Response()

    resolved = module.resolve_gap_pull_request(
        "https://github.com/gap-system/gap/pull/1234", token="TOKEN", get=fake_get
    )

    assert seen["url"] == "https://api.github.com/repos/gap-system/gap/pulls/1234"
    assert seen["headers"]["Authorization"] == "Bearer TOKEN"
    assert resolved["pr_url"] == "https://github.com/gap-system/gap/pull/1234"
    assert resolved["base_ref"] == "master"
    assert resolved["head_ref"] == "feature/test-pr"
    assert resolved["head_sha"] == "0123456789abcdef0123456789abcdef01234567"
    assert resolved["head_repo_clone_url"] == "https://github.com/contrib/gap.git"
    assert resolved["report_key"] == "pr-gap-system-gap-1234-01234567"
    assert resolved["report_label"] == "gap-system/gap#1234 @ 01234567 (base master)"
    assert resolved["job_name_prefix"] == "PR #1234"
