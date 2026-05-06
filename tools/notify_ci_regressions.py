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

import requests

ISSUE_LABEL = "ci-regression"
ISSUE_TITLE_PREFIX = "CI regression:"


def load_json(path: str) -> dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def changed_failures(
    test_status: dict[str, Any], previous_statuses: dict[str, str]
) -> list[dict[str, str]]:
    rows = []
    for pkg, data in sorted(test_status["pkgs"].items()):
        previous = previous_statuses.get(pkg)
        if data["status"] == "failure" and previous != "failure":
            rows.append(
                {
                    "name": pkg,
                    "version": data["version"],
                    "job_url": data["workflow_run"],
                    "previous_status": previous or "missing",
                }
            )
    return rows


def current_failures(test_status: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for pkg, data in sorted(test_status["pkgs"].items()):
        if data["status"] == "failure":
            rows.append(
                {
                    "name": pkg,
                    "version": data["version"],
                    "job_url": data["workflow_run"],
                }
            )
    return rows


def format_package_lines(rows: list[dict[str, str]]) -> str:
    return "\n".join(
        f"- {row['name']} {row['version']} ([failure]({row['job_url']}))"
        for row in rows
    )


def render_issue_body(
    which_gap: str,
    workflow_url: str,
    report_url: str,
    report_id: str,
    rows: list[dict[str, str]],
    mentions: list[str] | None = None,
) -> str:
    body = (
        f"Current package failures on GAP `{which_gap}`.\n\n"
        f"Report id: `{report_id}`\n\n"
        f"Workflow: {workflow_url}\n\n"
        f"Report: {report_url}\n\n"
        f"Current failures:\n{format_package_lines(rows)}\n\n"
    )
    if mentions:
        body += f"{' '.join(mentions)}\n"
    return body


def render_issue_comment(
    which_gap: str,
    workflow_url: str,
    report_url: str,
    report_id: str,
    rows: list[dict[str, str]],
) -> str:
    return (
        f"New regression event detected on GAP `{which_gap}`.\n\n"
        f"Report id: `{report_id}`\n\n"
        f"Workflow: {workflow_url}\n\n"
        f"Report: {report_url}\n\n"
        f"New failures:\n{format_package_lines(rows)}\n"
    )


def render_resolution_comment(
    which_gap: str,
    workflow_url: str,
    report_url: str,
    report_id: str,
) -> str:
    return (
        f"Latest report for GAP `{which_gap}` is now fully passing.\n\n"
        f"Report id: `{report_id}`\n\n"
        f"Workflow: {workflow_url}\n\n"
        f"Report: {report_url}\n"
    )


def find_open_incident_issue(
    session: requests.Session, repo: str, token: str, which_gap: str
) -> dict[str, Any] | None:
    url = f"https://api.github.com/repos/{repo}/issues"
    params: dict[str, str] = {
        "state": "open",
        "labels": ISSUE_LABEL,
        "per_page": "100",
    }
    expected_title = f"{ISSUE_TITLE_PREFIX} packages now failing on GAP {which_gap}"
    res = session.get(
        url,
        headers=github_headers(token),
        params=params,
    )
    res.raise_for_status()
    for issue in res.json():
        if issue["title"] == expected_title:
            return issue
    return None


def run_notification(
    session: requests.Session,
    repo: str,
    token: str,
    which_gap: str,
    mentions: list[str],
    test_status: dict[str, Any],
    report_diff: dict[str, Any],
    previous_statuses: dict[str, str] | None = None,
    report_url: str | None = None,
) -> dict[str, Any]:
    current_rows = current_failures(test_status)
    workflow_url = test_status["workflow"]
    issue = find_open_incident_issue(session, repo, token, which_gap)
    if not current_rows:
        if issue is None:
            return {"action": "noop", "issue_number": None}
        res = session.post(
            f"https://api.github.com/repos/{repo}/issues/{issue['number']}/comments",
            headers=github_headers(token),
            json={
                "body": render_resolution_comment(
                    which_gap,
                    workflow_url,
                    report_url or workflow_url,
                    test_status["id"],
                )
            },
        )
        res.raise_for_status()
        res = session.patch(
            f"https://api.github.com/repos/{repo}/issues/{issue['number']}",
            headers=github_headers(token),
            json={"state": "closed"},
        )
        res.raise_for_status()
        return {"action": "closed", "issue_number": issue["number"]}

    changed_rows = changed_failures(test_status, previous_statuses or {})
    title = f"{ISSUE_TITLE_PREFIX} packages now failing on GAP {which_gap}"
    if issue is None:
        body = render_issue_body(
            which_gap,
            workflow_url,
            report_url or workflow_url,
            test_status["id"],
            current_rows,
            mentions,
        )
        res = session.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers=github_headers(token),
            json={"title": title, "labels": [ISSUE_LABEL], "body": body},
        )
        res.raise_for_status()
        created = res.json()
        return {"action": "created", "issue_number": created["number"]}

    body = render_issue_body(
        which_gap,
        workflow_url,
        report_url or workflow_url,
        test_status["id"],
        current_rows,
    )
    res = session.patch(
        f"https://api.github.com/repos/{repo}/issues/{issue['number']}",
        headers=github_headers(token),
        json={"title": title, "body": body},
    )
    res.raise_for_status()
    if changed_rows:
        res = session.post(
            f"https://api.github.com/repos/{repo}/issues/{issue['number']}/comments",
            headers=github_headers(token),
            json={
                "body": render_issue_comment(
                    which_gap,
                    workflow_url,
                    report_url or workflow_url,
                    test_status["id"],
                    changed_rows,
                )
            },
        )
        res.raise_for_status()
    return {"action": "updated", "issue_number": issue["number"]}


def main(argv: list[str]) -> int:
    if len(argv) != 8:
        raise SystemExit(
            "usage: notify_ci_regressions.py TOKEN REPO WHICH_GAP "
            "MENTIONS TEST_STATUS REPORT_DIFF PREVIOUS_STATUS"
        )

    (
        token,
        repo,
        which_gap,
        mentions_arg,
        test_status_path,
        report_diff_path,
        previous_path,
    ) = argv[1:8]
    mentions = [entry for entry in mentions_arg.split(",") if entry]
    test_status = load_json(test_status_path)
    report_diff = load_json(report_diff_path)
    previous_statuses = load_json(previous_path)
    report_url = (
        f"{test_status['repo']}/blob/data/reports/{test_status['id']}/report.md"
    )
    session = requests.Session()
    result = run_notification(
        session=session,
        repo=repo,
        token=token,
        which_gap=which_gap,
        mentions=mentions,
        test_status=test_status,
        report_diff=report_diff,
        previous_statuses=previous_statuses,
        report_url=report_url,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
