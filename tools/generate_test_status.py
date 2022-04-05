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

from utils import error, warning, to_bool, normalize_pkg_name, metadata

import sys
import os
import glob
import json
from datetime import datetime
import requests

from typing import Any, Dict

################################################################################
# Arguments
num_args = len(sys.argv)

if num_args != 7:
    error("Unknown number of arguments")

git_token = sys.argv[1]
repo = sys.argv[2]
run_id = sys.argv[3]
hash = sys.argv[4]
which_gap = sys.argv[5]
job_name_prefix = sys.argv[6]

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
# Collect job information for all packages:
# Retrieve additional meta data about this workflow run via the REST API.
# We use this to figure out the status of all jobs
# as well as the numeric ids of all jobs, which we need
# to generate direct links to jobs in the final status report.
# https://stackoverflow.com/questions/33878019/how-to-get-data-from-all-pages-in-github-api-with-python
url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?simple=yes&per_page=100&page=1"
res = requests.get(url, headers={"Authorization": git_token})
jobs_list = res.json()["jobs"]
while "next" in res.links.keys():
    res = requests.get(res.links["next"]["url"], headers={"Authorization": git_token})
    jobs_list.extend(res.json()["jobs"])

# Turn list of jobs into a dictionary containing only the relevant data
jobs_dict: Dict[str, Any] = {}
for job in jobs_list:
    jobs_dict[job["name"]] = {
        "status": job["conclusion"],
        "workflow_run": job["html_url"],
    }
jobs_names = jobs_dict.keys()

# Direct link to job that constructs the test matrix.
# This is used for skipped packages
# that were not included in the test matrix.
name = f"{job_name_prefix}Build GAP and packages"
job = jobs_dict[name]
skipped_run = job["workflow_run"]

# Search for each package job name in jobs_dict
for pkg, data in pkgs.items():
    name = f"{job_name_prefix}{pkg}"
    if name in jobs_names:
        job = jobs_dict[name]
        # https://docs.github.com/en/actions/learn-github-actions/contexts#steps-context
        # Possible values for conclusion are success, failure, cancelled, or skipped.
        # We treat cancelled the same way as skipped
        status = job["status"]
        if status == "failure":
            data["status"] = "failure"
        elif status == "success":
            data["status"] = "success"
        else:  # cancelled or skipped
            data["status"] = "skipped"

        data["workflow_run"] = job["workflow_run"]
    else: # if pkg was skipped
        data["status"] = "skipped"
        data["workflow_run"] = skipped_run

################################################################################
# Generate main test-status.json

# General Information
report: Dict[str, Any] = {}
report["repo"] = os.path.join("https://github.com", repo)
report["workflow"] = os.path.join("https://github.com", repo, "actions", "runs", run_id)
report["hash"] = hash
date = str(datetime.now()).split(".")[0]
report["date"] = date
report["id"] = os.path.join(which_gap, "%s-%s" % (date.replace(" ", "-"), hash[:8]))

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

# Print id to terminal
print(report["id"])
