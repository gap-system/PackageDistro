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
import re
import sys
from typing import Any, Callable, Dict, Tuple

import requests
from utils import error

# This helper is the "front door" for ad hoc PR-triggered runs. The
# PackageDistro workflow accepts only a GAP PR URL, and this script turns that
# into the concrete clone/ref/SHA metadata needed by test-all.yml.
#
# The returned JSON is intentionally workflow-oriented rather than a direct copy
# of the GitHub API payload: downstream steps consume stable keys such as
# `report_key`, `report_label`, and `job_name_prefix`.
GAP_PR_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
    r"(?:[/?#].*)?$"
)


def github_headers(token: str | None) -> Dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def parse_gap_pull_request_url(url: str) -> Tuple[str, str, int]:
    # The current feature is deliberately scoped to GAP core PRs. Rejecting any
    # other repository early keeps the workflows and comments predictable.
    match = GAP_PR_URL_RE.match(url)
    if match is None:
        raise ValueError("Expected a GAP pull request URL on github.com")
    owner = match.group("owner")
    repo = match.group("repo")
    if (owner, repo) != ("gap-system", "gap"):
        raise ValueError("Expected a GAP pull request URL for gap-system/gap")
    return owner, repo, int(match.group("number"))


def build_report_key(owner: str, repo: str, number: int, head_sha: str) -> str:
    # `report_key` becomes part of the artifact name and report path under
    # data/reports/. It must be stable for a given PR head but distinct from the
    # baseline branch key such as "master".
    return f"pr-{owner}-{repo}-{number}-{head_sha[:8]}".lower()


def build_report_label(
    owner: str, repo: str, number: int, head_sha: str, base_ref: str
) -> str:
    return f"{owner}/{repo}#{number} @ {head_sha[:8]} (base {base_ref})"


def resolve_gap_pull_request(
    url: str,
    token: str | None = None,
    get: Callable[..., requests.Response] = requests.get,
) -> Dict[str, Any]:
    # Resolve the PR once up front so the rest of the workflow can stay simple:
    # it just consumes normalized metadata instead of duplicating API parsing in
    # shell.
    owner, repo, number = parse_gap_pull_request_url(url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
    response = get(api_url, headers=github_headers(token))
    response.raise_for_status()
    payload = response.json()

    base_ref = payload["base"]["ref"]
    head_sha = payload["head"]["sha"]
    # The downstream workflow needs both the user-facing branch name (`head_ref`)
    # and the exact commit (`head_sha`). test-all.yml clones the branch and then
    # verifies that the current tip still matches this SHA so a moving PR head is
    # detected explicitly instead of silently testing newer code.
    normalized = {
        "pr_url": f"https://github.com/{owner}/{repo}/pull/{number}",
        "api_url": api_url,
        "repo_owner": owner,
        "repo_name": repo,
        "repo_full_name": f"{owner}/{repo}",
        "number": number,
        "title": payload["title"],
        "base_ref": base_ref,
        "base_repo_full_name": payload["base"]["repo"]["full_name"],
        "base_repo_clone_url": payload["base"]["repo"]["clone_url"],
        "head_ref": payload["head"]["ref"],
        "head_sha": head_sha,
        "head_repo_full_name": payload["head"]["repo"]["full_name"],
        "head_repo_clone_url": payload["head"]["repo"]["clone_url"],
        "head_repo_html_url": payload["head"]["repo"]["html_url"],
        # These synthetic fields connect the resolver to the reporting pipeline.
        # They let ad hoc PR runs reuse the same report generation code as the
        # scheduled branch-based runs without colliding with branch report names.
        "report_key": build_report_key(owner, repo, number, head_sha),
        "report_label": build_report_label(owner, repo, number, head_sha, base_ref),
        "job_name_prefix": f"PR #{number}",
    }
    return normalized


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        error("usage: gap_pr_utils.py GAP_PR_URL [GITHUB_TOKEN]")
    token = argv[2] if len(argv) == 3 else None
    resolved = resolve_gap_pull_request(argv[1], token=token)
    print(json.dumps(resolved, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
