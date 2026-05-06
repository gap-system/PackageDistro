# -*- coding: utf-8 -*-
# pylint: disable=missing-function-docstring, invalid-name

import importlib
import os
import sys

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)


def test_run_returns_without_api_calls_when_no_failures_and_no_issue():
    module = importlib.import_module("notify_ci_regressions")
    calls = []

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
            calls.append(("get", url, params))
            return Response([])

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
    assert calls == [
        (
            "get",
            "https://api.github.com/repos/gap-system/PackageDistro/issues",
            {"state": "open", "labels": "ci-regression", "per_page": "100"},
        )
    ]


def test_run_closes_existing_incident_when_failures_clear():
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
            return Response({"number": 7550, "state": "closed"})

    result = module.run_notification(
        session=Session(),
        repo="gap-system/PackageDistro",
        token="TOKEN",
        which_gap="master",
        mentions=["@user1", "@user2"],
        test_status={
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/11",
            "id": "master/2026-04-26-01234567",
            "pkgs": {
                "atlasrep": {
                    "status": "success",
                    "version": "2.1",
                    "workflow_run": "https://example.invalid/job/atlasrep",
                }
            },
        },
        report_diff={"failure_changed": -1},
        previous_statuses={"atlasrep": "failure"},
        report_url="https://github.com/gap-system/PackageDistro/blob/data/reports/master/report.md",
    )

    assert result == {"action": "closed", "issue_number": 7550}
    assert len(seen["posts"]) == 1
    assert "fully passing" in seen["posts"][0][1]["body"]
    assert "master/2026-04-26-01234567" in seen["posts"][0][1]["body"]
    assert (
        "https://github.com/gap-system/PackageDistro/actions/runs/11"
        in seen["posts"][0][1]["body"]
    )
    assert (
        "https://github.com/gap-system/PackageDistro/blob/data/reports/master/report.md"
        in seen["posts"][0][1]["body"]
    )
    assert seen["patches"][0][1]["state"] == "closed"


def test_run_closes_existing_incident_only_for_matching_gap_target():
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
                        "number": 7001,
                        "title": "CI regression: packages now failing on GAP stable-4.14",
                        "labels": [{"name": "ci-regression"}],
                    },
                    {
                        "number": 7550,
                        "title": "CI regression: packages now failing on GAP master",
                        "labels": [{"name": "ci-regression"}],
                    },
                ]
            )

        def post(self, url, headers=None, json=None):
            seen["posts"].append((url, json))
            return Response({"id": 1})

        def patch(self, url, headers=None, json=None):
            seen["patches"].append((url, json))
            return Response({"number": 7550, "state": "closed"})

    result = module.run_notification(
        session=Session(),
        repo="gap-system/PackageDistro",
        token="TOKEN",
        which_gap="master",
        mentions=["@user1", "@user2"],
        test_status={
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/12",
            "id": "master/2026-04-27-89abcdef",
            "pkgs": {
                "atlasrep": {
                    "status": "success",
                    "version": "2.1",
                    "workflow_run": "https://example.invalid/job/atlasrep",
                }
            },
        },
        report_diff={"failure_changed": -1},
        previous_statuses={"atlasrep": "failure"},
        report_url="https://github.com/gap-system/PackageDistro/blob/data/reports/master/report.md",
    )

    assert result == {"action": "closed", "issue_number": 7550}
    assert len(seen["posts"]) == 1
    assert "/issues/7550/comments" in seen["posts"][0][0]
    assert len(seen["patches"]) == 1
    assert seen["patches"][0][0].endswith("/issues/7550")
    assert seen["patches"][0][1]["state"] == "closed"


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


def test_run_creates_incident_issue_for_current_failures_when_missing():
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
            return Response(
                [
                    {
                        "number": 7001,
                        "title": "CI regression: packages now failing on GAP stable-4.14",
                        "labels": [{"name": "ci-regression"}],
                    }
                ]
            )

        def post(self, url, headers=None, json=None):
            seen["posts"].append((url, json))
            return Response({"number": 4022})

        def patch(self, *args, **kwargs):
            raise AssertionError("patch should not be called")

    result = module.run_notification(
        session=Session(),
        repo="gap-system/PackageDistro",
        token="TOKEN",
        which_gap="master",
        mentions=["@user1", "@user2"],
        test_status={
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/13",
            "id": "master/2026-04-28-a1b2c3d4",
            "pkgs": {
                "atlasrep": {
                    "status": "failure",
                    "version": "2.1",
                    "workflow_run": "https://example.invalid/job/atlasrep",
                },
                "guava": {
                    "status": "failure",
                    "version": "3.0",
                    "workflow_run": "https://example.invalid/job/guava",
                },
            },
        },
        report_diff={"failure_changed": 0},
        previous_statuses={"atlasrep": "failure", "guava": "failure"},
        report_url="https://github.com/gap-system/PackageDistro/blob/data/reports/master/report.md",
    )

    assert result == {"action": "created", "issue_number": 4022}
    assert len(seen["posts"]) == 1
    body = seen["posts"][0][1]["body"]
    assert "Current package failures on GAP `master`." in body
    assert "atlasrep 2.1" in body
    assert "guava 3.0" in body
    assert "@user1 @user2" in body


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
                },
                "guava": {
                    "status": "failure",
                    "version": "3.0",
                    "workflow_run": "https://example.invalid/job/guava",
                },
            },
        },
        report_diff={"failure_changed": 1},
        previous_statuses={"atlasrep": "failure", "guava": "success"},
        report_url="https://github.com/gap-system/PackageDistro/blob/data/reports/master/report.md",
    )

    assert result == {"action": "updated", "issue_number": 7550}
    assert len(seen["patches"]) == 1
    assert len(seen["posts"]) == 1
    patch_body = seen["patches"][0][1]["body"]
    assert (
        seen["posts"][0][0]
        == "https://api.github.com/repos/gap-system/PackageDistro/issues/7550/comments"
    )
    comment_body = seen["posts"][0][1]["body"]

    assert "Current package failures on GAP `master`." in patch_body
    assert "Current failures:" in patch_body
    assert "atlasrep 2.1" in patch_body
    assert "guava 3.0" in patch_body

    assert "New regression event detected on GAP `master`." in comment_body
    assert "New failures:" in comment_body
    assert "atlasrep 2.1" not in comment_body
    assert "guava 3.0" in comment_body

    assert "@user1" not in patch_body
    assert "@user2" not in patch_body
    assert "@user1" not in comment_body
    assert "@user2" not in comment_body


def test_run_updates_existing_incident_and_comments_for_mixed_delta():
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
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/14",
            "id": "master/2026-04-29-0badcafe",
            "pkgs": {
                "atlasrep": {
                    "status": "success",
                    "version": "2.1",
                    "workflow_run": "https://example.invalid/job/atlasrep",
                },
                "guava": {
                    "status": "failure",
                    "version": "3.0",
                    "workflow_run": "https://example.invalid/job/guava",
                },
            },
        },
        report_diff={"failure_changed": 0},
        previous_statuses={"atlasrep": "failure", "guava": "success"},
        report_url="https://github.com/gap-system/PackageDistro/blob/data/reports/master/report.md",
    )

    assert result == {"action": "updated", "issue_number": 7550}
    assert len(seen["patches"]) == 1
    assert len(seen["posts"]) == 1
    patch_body = seen["patches"][0][1]["body"]
    comment_body = seen["posts"][0][1]["body"]

    assert "Current package failures on GAP `master`." in patch_body
    assert "atlasrep 2.1" not in patch_body
    assert "guava 3.0" in patch_body

    assert "New regression event detected on GAP `master`." in comment_body
    assert "atlasrep 2.1" not in comment_body
    assert "guava 3.0" in comment_body


def test_run_updates_existing_incident_for_current_failures_without_comment():
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
            raise AssertionError("post should not be called")

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
                },
                "guava": {
                    "status": "failure",
                    "version": "3.0",
                    "workflow_run": "https://example.invalid/job/guava",
                },
            },
        },
        report_diff={"failure_changed": 0},
        previous_statuses={"atlasrep": "failure", "guava": "failure"},
        report_url="https://github.com/gap-system/PackageDistro/blob/data/reports/master/report.md",
    )

    assert result == {"action": "updated", "issue_number": 7550}
    assert len(seen["patches"]) == 1
    assert "Current package failures on GAP `master`." in seen["patches"][0][1]["body"]
    assert "Current failures:" in seen["patches"][0][1]["body"]
    assert "atlasrep 2.1" in seen["patches"][0][1]["body"]
    assert "guava 3.0" in seen["patches"][0][1]["body"]
    assert seen["posts"] == []
