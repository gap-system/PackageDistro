# -*- coding: utf-8 -*-
# pylint: disable=missing-function-docstring, invalid-name

import importlib
import os
import sys

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)


def test_run_returns_without_api_calls_when_no_new_failures():
    module = importlib.import_module("notify_ci_regressions")
    calls = []

    class Session:
        def get(self, *args, **kwargs):
            calls.append(("get", args, kwargs))
            raise AssertionError("GitHub API should not be queried")

        def post(self, *args, **kwargs):
            calls.append(("post", args, kwargs))
            raise AssertionError("GitHub API should not be queried")

        def patch(self, *args, **kwargs):
            calls.append(("patch", args, kwargs))
            raise AssertionError("GitHub API should not be queried")

    result = module.run_notification(
        session=Session(),
        repo="gap-system/PackageDistro",
        token="TOKEN",
        which_gap="master",
        mentions=["@user1", "@user2"],
        test_status={
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/1",
            "id": "master/2026-04-24-abcdef12",
            "pkgs": {
                "atlasrep": {
                    "status": "success",
                    "version": "2.1",
                    "workflow_run": "https://example.invalid/job/atlasrep",
                }
            },
        },
        report_diff={"failure_changed": 0},
    )

    assert result == {"action": "noop", "issue_number": None}
    assert calls == []


def test_run_creates_incident_issue_with_mentions_for_first_regression():
    module = importlib.import_module("notify_ci_regressions")
    seen = {"posts": []}

    class Response:
        def __init__(self, payload):
            self.payload = payload
            self.links = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def get(self, url, headers=None, params=None):
            assert url.endswith("/repos/gap-system/PackageDistro/issues")
            assert params["state"] == "open"
            assert params["labels"] == "ci-regression"
            return Response([])

        def post(self, url, headers=None, json=None):
            seen["posts"].append((url, json))
            return Response({"number": 4021})

        def patch(self, *args, **kwargs):
            raise AssertionError("patch should not be called")

    result = module.run_notification(
        session=Session(),
        repo="gap-system/PackageDistro",
        token="TOKEN",
        which_gap="master",
        mentions=["@user1", "@user2"],
        test_status={
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/9",
            "id": "master/2026-04-24-abcdef12",
            "pkgs": {
                "atlasrep": {
                    "status": "failure",
                    "version": "2.1",
                    "workflow_run": "https://example.invalid/job/atlasrep",
                },
                "guava": {
                    "status": "success",
                    "version": "3.0",
                    "workflow_run": "https://example.invalid/job/guava",
                },
            },
        },
        report_diff={"failure_changed": 1},
        previous_statuses={"atlasrep": "success", "guava": "success"},
        report_url="https://github.com/gap-system/PackageDistro/blob/data/reports/master/report.md",
    )

    assert result == {"action": "created", "issue_number": 4021}
    body = seen["posts"][0][1]["body"]
    assert "@user1 @user2" in body
    assert "atlasrep 2.1" in body
    assert (
        "CI regression: packages now failing on GAP master"
        == seen["posts"][0][1]["title"]
    )


def test_run_updates_existing_incident_and_comments_without_mentions():
    module = importlib.import_module("notify_ci_regressions")
    seen = {"patches": [], "posts": []}

    class Response:
        def __init__(self, payload):
            self.payload = payload
            self.links = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def get(self, url, headers=None, params=None):
            return Response(
                [
                    {
                        "number": 7550,
                        "title": "CI regression: packages now failing on GAP master",
                        "labels": [{"name": "ci-regression"}],
                    }
                ]
            )

        def post(self, url, headers=None, json=None):
            seen["posts"].append((url, json))
            return Response({"id": 1})

        def patch(self, url, headers=None, json=None):
            seen["patches"].append((url, json))
            return Response({"number": 7550})

    result = module.run_notification(
        session=Session(),
        repo="gap-system/PackageDistro",
        token="TOKEN",
        which_gap="master",
        mentions=["@user1", "@user2"],
        test_status={
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/10",
            "id": "master/2026-04-25-fedcba98",
            "pkgs": {
                "atlasrep": {
                    "status": "failure",
                    "version": "2.1",
                    "workflow_run": "https://example.invalid/job/atlasrep",
                }
            },
        },
        report_diff={"failure_changed": 1},
        previous_statuses={"atlasrep": "success"},
        report_url="https://github.com/gap-system/PackageDistro/blob/data/reports/master/report.md",
    )

    assert result == {"action": "updated", "issue_number": 7550}
    assert "@user1" not in seen["posts"][0][1]["body"]
    assert "@user1" not in seen["patches"][0][1]["body"]
    assert "atlasrep 2.1" in seen["patches"][0][1]["body"]
