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

import json
import sys
from typing import Any

from utils import error

COMMENT_MARKER = "<!-- gap-package-distribution-bot:gap-pr-test -->"


def load_json(path: str) -> dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def load_text(path: str) -> str:
    with open(path, "r") as f:
        return f.read().strip()


def package_links(
    package_names: list[str], test_status: dict[str, Any], limit: int = 10
) -> str:
    rows = []
    for name in package_names[:limit]:
        pkg = test_status["pkgs"][name]
        rows.append(f"- [{name} {pkg['version']}]({pkg['workflow_run']})")
    if len(package_names) > limit:
        rows.append(f"- ... and {len(package_names) - limit} more")
    return "\n".join(rows)


def render_gap_pr_comment(
    metadata: dict[str, Any],
    test_status: dict[str, Any],
    report_diff: dict[str, Any],
    report_markdown: str,
) -> str:
    repo_full_name = metadata["repo_full_name"]
    number = metadata["number"]
    head_sha = metadata["head_sha"][:8]
    workflow_url = test_status["workflow"]

    lines = [
        COMMENT_MARKER,
        f"## PackageDistro test for {repo_full_name}#{number}",
        "",
        f"- PR: {metadata['pr_url']}",
        f"- Tested head SHA: `{head_sha}`",
        f"- Workflow: [workflow run]({workflow_url})",
        (
            f"- Summary: {test_status['success']} succeeded, "
            f"{test_status['failure']} failed, {test_status['skipped']} skipped"
        ),
    ]

    requester = metadata.get("requester")
    command = metadata.get("command")
    if requester and command:
        lines.append(f"- Requested by @{requester} via `{command}`.")

    lines.append("")

    failures_changed = report_diff.get("failures_changed", [])
    failures_current = report_diff.get("failures_current", [])
    if report_diff.get("failure_changed", 0) > 0 and failures_changed:
        lines.append("### New failures vs baseline")
        lines.append("")
        lines.append(package_links(failures_changed, test_status))
        lines.append("")
    elif test_status.get("failure", 0) > 0 and failures_current:
        lines.append("### Current failing packages")
        lines.append("")
        lines.append(package_links(failures_current, test_status))
        lines.append("")

    lines.extend(
        [
            "<details>",
            "<summary>Full report</summary>",
            "",
            report_markdown.strip(),
            "",
            "</details>",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        error(
            "usage: render_gap_pr_test_comment.py "
            "METADATA_JSON TEST_STATUS_JSON REPORT_DIFF_JSON REPORT_MD"
        )
    metadata = load_json(argv[1])
    test_status = load_json(argv[2])
    report_diff = load_json(argv[3])
    report_markdown = load_text(argv[4])
    print(
        render_gap_pr_comment(
            metadata=metadata,
            test_status=test_status,
            report_diff=report_diff,
            report_markdown=report_markdown,
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
