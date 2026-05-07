# -*- coding: utf-8 -*-
# pylint: disable=missing-function-docstring, invalid-name

import importlib
import os
import sys

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)


def test_render_gap_pr_comment_reports_new_failures():
    module = importlib.import_module("render_gap_pr_test_comment")

    body = module.render_gap_pr_comment(
        metadata={
            "pr_url": "https://github.com/gap-system/gap/pull/1234",
            "repo_full_name": "gap-system/gap",
            "number": 1234,
            "head_sha": "0123456789abcdef0123456789abcdef01234567",
            "requester": "fingolfin",
            "command": "@gap-package-distribution-bot test",
        },
        test_status={
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/77",
            "success": 120,
            "failure": 2,
            "skipped": 3,
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
        report_diff={"failure_changed": 1, "failures_changed": ["atlasrep"]},
        report_markdown="# Package Evaluation Report\n\nDetails here.\n",
    )

    assert "gap-system/gap#1234" in body
    assert "Requested by @fingolfin via `@gap-package-distribution-bot test`." in body
    assert "`01234567`" in body
    assert (
        "[workflow run](https://github.com/gap-system/PackageDistro/actions/runs/77)"
        in body
    )
    assert "120 succeeded, 2 failed, 3 skipped" in body
    assert "New failures vs baseline" in body
    assert "[atlasrep 2.1](https://example.invalid/job/atlasrep)" in body
    assert "<!-- gap-package-distribution-bot:gap-pr-test -->" in body


def test_render_gap_pr_comment_reports_current_failures_when_no_regressions():
    module = importlib.import_module("render_gap_pr_test_comment")

    body = module.render_gap_pr_comment(
        metadata={
            "pr_url": "https://github.com/gap-system/gap/pull/1234",
            "repo_full_name": "gap-system/gap",
            "number": 1234,
            "head_sha": "fedcba9876543210fedcba9876543210fedcba98",
        },
        test_status={
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/88",
            "success": 100,
            "failure": 1,
            "skipped": 0,
            "pkgs": {
                "atlasrep": {
                    "status": "failure",
                    "version": "2.1",
                    "workflow_run": "https://example.invalid/job/atlasrep",
                }
            },
        },
        report_diff={"failure_changed": 0, "failures_current": ["atlasrep"]},
        report_markdown="# Package Evaluation Report\n\nDetails here.\n",
    )

    assert "Current failing packages" in body
    assert "[atlasrep 2.1](https://example.invalid/job/atlasrep)" in body
    assert "New failures vs baseline" not in body
