#!/usr/bin/env python3

#############################################################################
##
##  This file is part of GAP, a system for computational discrete algebra.
##
##  Copyright of GAP belongs to its developers, whose names are too numerous
##  to list. Please refer to the COPYRIGHT file for details.
##
##  SPDX-License-Identifier: GPL-2.0-or-later
##

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Callable

import utils

RunGh = Callable[[list[str]], subprocess.CompletedProcess[str]]
NOBLOCK_MARKER = "[noblock]"

PR_FIELDS = ",".join(
    [
        "number",
        "title",
        "url",
        "createdAt",
        "headRefName",
        "headRefOid",
        "headRepositoryOwner",
        "isDraft",
        "labels",
    ]
)


def parse_github_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def label_names(pr: dict[str, Any]) -> set[str]:
    return {label["name"] for label in pr.get("labels", [])}


def pr_age_seconds(pr: dict[str, Any], now: datetime) -> int:
    return int((now - parse_github_datetime(pr["createdAt"])).total_seconds())


def is_candidate_pull_request(
    pr: dict[str, Any],
    repository_owner: str,
    minimum_age_seconds: int,
    now: datetime,
) -> bool:
    labels = label_names(pr)
    head_owner = pr.get("headRepositoryOwner", {}).get("login")
    return (
        not pr["isDraft"]
        and pr["headRefName"].startswith("automatic/")
        and head_owner == repository_owner
        and "automated pr" in labels
        and "package update" in labels
        and "new package" not in labels
        and pr_age_seconds(pr, now) >= minimum_age_seconds
    )


def filter_candidate_pull_requests(
    prs: list[dict[str, Any]],
    repository_owner: str,
    minimum_age_seconds: int,
    now: datetime,
) -> list[dict[str, Any]]:
    return [
        pr
        for pr in prs
        if is_candidate_pull_request(pr, repository_owner, minimum_age_seconds, now)
    ]


def run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        capture_output=True,
        check=False,
        encoding="UTF-8",
    )


def gh_json(args: list[str], run: RunGh) -> tuple[int, Any, str]:
    result = run(args)
    if result.stdout:
        return result.returncode, json.loads(result.stdout), result.stderr
    return result.returncode, None, result.stderr


def list_pull_requests(limit: int, run: RunGh) -> list[dict[str, Any]]:
    returncode, data, stderr = gh_json(
        ["pr", "list", "--state", "open", "--limit", str(limit), "--json", PR_FIELDS],
        run,
    )
    if returncode != 0:
        utils.error(f"gh pr list failed: {stderr}")
    return data


def list_issue_comments(
    repository: str, number: int, run: RunGh
) -> list[dict[str, Any]]:
    returncode, data, stderr = gh_json(
        [
            "api",
            f"repos/{repository}/issues/{number}/comments",
            "--paginate",
            "--slurp",
        ],
        run,
    )
    if returncode != 0:
        msg = f"Could not read comments for PR #{number}; refusing to merge."
        if stderr:
            msg += f"\n{stderr.rstrip()}"
        utils.error(msg)
    if data and isinstance(data[0], list):
        return [comment for page in data for comment in page]
    return data


def is_blocking_comment(comment: dict[str, Any]) -> bool:
    user = comment.get("user") or {}
    if user.get("type") == "Bot":
        return False
    return NOBLOCK_MARKER not in comment.get("body", "").lower()


def blocking_comments(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [comment for comment in comments if is_blocking_comment(comment)]


def has_blocking_comments(repository: str, number: int, run: RunGh) -> bool:
    comments = list_issue_comments(repository, number, run)
    blockers = blocking_comments(comments)
    if blockers:
        print(f"PR #{number} has blocking comments:")
        for comment in blockers:
            user = comment.get("user") or {}
            print(f"- {user.get('login', 'unknown')}: {comment.get('html_url', '')}")
        return True

    return False


def required_checks_pass(number: int, run: RunGh) -> bool:
    returncode, checks, stderr = gh_json(
        ["pr", "checks", str(number), "--required", "--json", "name,bucket,state"],
        run,
    )
    if returncode != 0:
        print(f"Required checks for PR #{number} are not all passing or unreadable.")
        if checks:
            for check in checks:
                print(f"- {check['name']}: {check['state']}")
        elif stderr:
            print(stderr.rstrip())
        return False

    if not checks:
        print(f"PR #{number} has no required checks; refusing to merge.")
        return False

    failing_checks = [check for check in checks if check["bucket"] != "pass"]
    if failing_checks:
        print(f"Required checks for PR #{number} are not all passing:")
        for check in failing_checks:
            print(f"- {check['name']}: {check['state']}")
        return False

    return True


def merge_pull_request(pr: dict[str, Any], run: RunGh) -> None:
    number = str(pr["number"])
    result = run(
        [
            "pr",
            "merge",
            number,
            "--squash",
            "--delete-branch",
            "--match-head-commit",
            pr["headRefOid"],
        ]
    )
    if result.returncode != 0:
        msg = f"Merge failed for PR #{number}; leaving it open."
        if result.stderr:
            msg += f"\n{result.stderr.rstrip()}"
        utils.error(msg)


def auto_merge_package_updates(
    repository: str,
    repository_owner: str,
    minimum_age_seconds: int,
    dry_run: bool,
    now: datetime | None = None,
    limit: int = 100,
    run_gh: RunGh = run_gh,
) -> list[int]:
    if now is None:
        now = datetime.now(timezone.utc)

    candidates = filter_candidate_pull_requests(
        list_pull_requests(limit, run_gh),
        repository_owner=repository_owner,
        minimum_age_seconds=minimum_age_seconds,
        now=now,
    )

    if not candidates:
        print("No eligible package update pull requests found.")
        return []

    merged: list[int] = []
    for pr in candidates:
        number = pr["number"]
        title = pr["title"]
        if has_blocking_comments(repository, number, run_gh):
            continue

        if not required_checks_pass(number, run_gh):
            continue

        if dry_run:
            print(f"Would merge PR #{number}: {title}")
            print(pr["url"])
            merged.append(number)
        else:
            merge_pull_request(pr, run_gh)
            print(f"Merged PR #{number}: {title}")
            merged.append(number)

    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Auto-merge eligible package update pull requests."
    )
    parser.add_argument(
        "--repository",
        required=True,
        help="GitHub repository in OWNER/NAME form.",
    )
    parser.add_argument(
        "--repository-owner",
        required=True,
        help="Repository owner used to reject pull requests from forks.",
    )
    parser.add_argument(
        "--minimum-age-seconds",
        type=int,
        required=True,
        help="Minimum PR age before merging.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of open pull requests to inspect.",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Print pull requests that would be merged without merging them.",
    )
    args = parser.parse_args(argv)

    auto_merge_package_updates(
        repository=args.repository,
        repository_owner=args.repository_owner,
        minimum_age_seconds=args.minimum_age_seconds,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
