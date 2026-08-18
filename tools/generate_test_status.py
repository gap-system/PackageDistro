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

"""
This script collects the job-status of each package from _reports/
and generates a main test-status.json.

The file is written into data/reports/{{id}} where
id={{report_key}}/{{YYYY}}/{{MM}}/{{DD}}_{{HH-mm-ss}}.

Prints {{id}} to terminal.
"""

# The name of a job is HARDCODED.
# If we change the name of a job in the test-all YML file,
# or use a different prefix from a caller (like the test-all-and-report YML file),
# then we need to adjust the hardcoded names in this python script.

import glob
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, NotRequired, TypedDict

import requests
from utils import _should_retry, error, metadata, normalize_pkg_name, warning

GITHUB_API_ATTEMPTS = 4
GITHUB_API_TIMEOUT = (30, 60)


class JobInfo(TypedDict):
    status: str | None
    workflow_run: str
    completed_at: NotRequired[str | None]


def github_headers(git_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {git_token}"}


def response_jobs(res: requests.Response, url: str) -> List[Dict[str, Any]]:
    payload = res.json()
    jobs = payload.get("jobs")
    if jobs is None:
        warning(f'GitHub API response for "{url}" did not contain a "jobs" key')
        return []
    return jobs


def fetch_jobs(
    git_token: str,
    repo: str,
    run_id: str,
    get: Callable[..., requests.Response] = requests.get,
) -> List[Dict[str, Any]]:
    # `latest` gives us one job per name after a partial rerun, without making
    # GitHub construct and paginate responses containing every prior attempt.
    # Smaller pages also avoid intermittent gateway errors seen on large runs.
    url = (
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs"
        "?simple=yes&filter=latest&per_page=50&page=1"
    )
    headers = github_headers(git_token)
    jobs_list: List[Dict[str, Any]] = []
    while url:
        for attempt in range(1, GITHUB_API_ATTEMPTS + 1):
            try:
                res = get(url, headers=headers, timeout=GITHUB_API_TIMEOUT)
                res.raise_for_status()
                break
            except requests.RequestException as exc:
                if attempt == GITHUB_API_ATTEMPTS or not _should_retry(exc):
                    raise
                warning(f'GitHub API request for "{url}" failed ({exc}), retrying')
                time.sleep(2**attempt)
        jobs_list.extend(response_jobs(res, url))
        url = res.links.get("next", {}).get("url", "")
    return jobs_list


def report_id(report_key: str, date: str) -> str:
    """The storage location of a report, relative to data/reports.

    `date` is a timestamp of the form "YYYY-MM-DD HH:mm:ss". Year and month
    become directories of their own: a flat directory per report leaves the
    `data` branch with thousands of sibling directories, which GitHub's file
    browser is of no use for. See issue #1120.

    The time is written as "HH-mm-ss" rather than with colons, which several
    file systems reject, and an underscore separates the day from the time so
    that the two halves stay apart at a glance. The timestamp alone identifies
    a report: at most one run per report key is in flight at any time, so the
    tested revision does not have to disambiguate the path, and the report
    names it in its own text instead.
    """
    day_part, time_part = date.split(" ")
    year, month, day = day_part.split("-")
    time = time_part.replace(":", "-")
    return os.path.join(report_key, year, month, f"{day}_{time}")


def job_is_newer(job: Dict[str, Any], current_job: JobInfo) -> bool:
    completed_at = job.get("completed_at") or ""
    current_completed_at = current_job.get("completed_at") or ""
    return completed_at >= current_completed_at


def main(argv: List[str]) -> int:
    ################################################################################
    # Arguments
    num_args = len(argv)

    if num_args not in (7, 8):
        error("Unknown number of arguments")

    git_token = argv[1]
    repo = argv[2]
    run_id = argv[3]
    hash = argv[4]
    report_key = argv[5]
    if num_args == 8:
        # Ad hoc PR runs pass a stable storage key plus a friendlier display
        # label. Scheduled branch-based runs still use the older 7-argument
        # calling convention in which the key also serves as the display name.
        gap_display_name = argv[6]
        job_name_prefix = argv[7]
    else:
        gap_display_name = report_key
        job_name_prefix = argv[6]

    ################################################################################
    # Collect names of all packages
    files = []
    for file in glob.glob("packages/*/meta.json"):
        files.append(file)

    files.sort()
    pkgs: Dict[str, Any] = {}

    for file in files:
        pkgs[normalize_pkg_name(file)] = {}

    ################################################################################
    # Collect job information for all packages
    jobs_list = fetch_jobs(git_token, repo, run_id)

    # Turn list of jobs into a dictionary containing only the relevant data.
    # Keep the most recent job defensively in case the API returns duplicate
    # names despite filter=latest.
    jobs_dict: Dict[str, JobInfo] = {}
    for raw_job in jobs_list:
        name = raw_job["name"]
        current_job = jobs_dict.get(name)
        if current_job is None or job_is_newer(raw_job, current_job):
            jobs_dict[name] = {
                "status": raw_job["conclusion"],
                "workflow_run": raw_job["html_url"],
                "completed_at": raw_job.get("completed_at"),
            }

    workflow_run_url = os.path.join(
        "https://github.com", repo, "actions", "runs", run_id
    )

    # Direct link to job that constructs the test matrix.
    # This is used for skipped packages that were not included in the test matrix.
    name = f"{job_name_prefix}Build GAP and packages"
    build_job = jobs_dict.get(name)
    if build_job is None:
        warning(f'Could not find job "{name}" in workflow run {run_id}')
        skipped_run = workflow_run_url
    else:
        skipped_run = build_job["workflow_run"]

    # Add status and direct link to workflow for all packages
    for pkg, data in pkgs.items():
        name = f"{job_name_prefix}{pkg}"
        pkg_job = jobs_dict.get(name)
        if pkg_job is not None:
            # https://docs.github.com/en/actions/learn-github-actions/contexts#steps-context
            # Possible values for conclusion are success, failure, cancelled, or skipped.
            # We treat cancelled the same way as skipped.
            status = pkg_job["status"]
            if status == "failure":
                data["status"] = "failure"
            elif status == "success":
                data["status"] = "success"
            else:  # cancelled or skipped
                data["status"] = "skipped"

            data["workflow_run"] = pkg_job["workflow_run"]
        else:  # if pkg was skipped
            data["status"] = "skipped"
            data["workflow_run"] = skipped_run

    ################################################################################
    # Generate main test-status.json

    # General Information
    report: Dict[str, Any] = {}
    report["repo"] = os.path.join("https://github.com", repo)
    report["workflow"] = workflow_run_url
    report["hash"] = hash
    date = str(datetime.now()).split(".")[0]
    report["date"] = date
    report["gap_version"] = gap_display_name
    # `gap_report_key` is the machine-oriented identifier used to pick the
    # storage location and compare against the right baseline. For regular runs
    # it is just "master" etc.; for PR-triggered runs it is a synthetic key
    # such as "pr-gap-system-gap-1234-deadbeef".
    report["gap_report_key"] = report_key
    report["id"] = report_id(report_key, date)

    # Path
    root = "data/reports"
    dir_test_status = os.path.join(root, report["id"])
    os.makedirs(dir_test_status, exist_ok=True)

    # Package Information
    for pkg, data in pkgs.items():
        pkg_json = metadata(pkg)
        data["version"] = pkg_json["Version"]
        data["archive_url"] = pkg_json["ArchiveURL"]
        data["archive_sha256"] = pkg_json["ArchiveSHA256"]

    report["pkgs"] = pkgs

    # Summary Information
    report["total"] = 0
    report["success"] = 0
    report["failure"] = 0
    report["skipped"] = 0

    for pkg, data in pkgs.items():
        report["total"] += 1
        status = data["status"]
        if status == "success":
            report["success"] += 1
        elif status == "failure":
            report["failure"] += 1
        elif status == "skipped":
            report["skipped"] += 1
        else:
            warning('Unknown job status detected for pkg "' + pkg + '"')

    with open(os.path.join(dir_test_status, "test-status.json"), "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Print id to terminal, so that the workflow scripts can parse the output.
    print(report["id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
