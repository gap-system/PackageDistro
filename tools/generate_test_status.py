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
id={{which_gap}}/{{date}}-{{hash_short}}.

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
from datetime import datetime
from typing import Any, Callable, Dict, List, NotRequired, TypedDict

import requests
from utils import error, metadata, normalize_pkg_name, warning


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
    # Use filter=all so rerunning a single matrix job still lets us see the
    # jobs from previous attempts of the same workflow run.
    url = (
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs"
        "?simple=yes&filter=all&per_page=100&page=1"
    )
    headers = github_headers(git_token)
    res = get(url, headers=headers)
    res.raise_for_status()
    jobs_list = response_jobs(res, url)
    while "next" in res.links.keys():
        url = res.links["next"]["url"]
        res = get(url, headers=headers)
        res.raise_for_status()
        jobs_list.extend(response_jobs(res, url))
    return jobs_list


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
    # With filter=all a rerun may contain multiple jobs with the same name, so
    # keep the most recent one according to completed_at.
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
    report["gap_report_key"] = report_key
    report["id"] = os.path.join(
        report_key, "%s-%s" % (date.replace(" ", "-"), hash[:8])
    )

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
