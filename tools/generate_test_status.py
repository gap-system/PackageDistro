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

from typing import Any, Dict

################################################################################
# Arguments
num_args = len(sys.argv)

if num_args > 6:
    error("Too many arguments")

repo = runID = hash = which_gap = "Unknown"
is_workflow_call = False

if num_args > 1:
    repo = "https://github.com/" + sys.argv[1]
if num_args > 2:
    runID = sys.argv[2]
if num_args > 3:
    hash = sys.argv[3]
if num_args > 4:
    which_gap = sys.argv[4]
if num_args > 5:
    is_workflow_call = to_bool(sys.argv[5])

################################################################################
# Collect names of all packages
files = []
for file in glob.glob("packages/*/meta.json", recursive=True):
    files.append(file)

files.sort()
pkgs = {}

for file in files:
    pkgs[normalize_pkg_name(file)] = {}

################################################################################
# Collect job information for all packages
with open("jobs.json", "r", encoding="utf-8", error="ignore") as f:
    jobs = json.load(f)["jobs"]

# job_id for skipped packages
if is_workflow_call:
    name=f"{which_gap} / Build GAP and packages"
else:
    name="Build GAP and packages"

for job in jobs:
    if job["name"] == name:
        skipped_job_id = job["id"]
    break

# Search for each package job name in the list of jobs
for pkg, data in pkgs.items():
    # if pkg was tested
    if is_workflow_call:
        name=f"{which_gap} / {pkg}"
    else:
        name="{pkg}"

    for job in jobs:
        if job["name"] == name:
            # https://docs.github.com/en/actions/learn-github-actions/contexts#steps-context
            # Possible values for conclusion are success, failure, cancelled, or skipped.
            # We treat cancelled the same way as skipped
            status = job["conclusion"]
            if status == "failure":
                data["status"] = "failure"
            elif status == "success":
                data["status"] = "success"
            else: # cancelled or skipped
                data["status"] = "skipped"

            # numerical job id
            data["job_id"] = job["id"]
            break

    # if pkg was skipped
    if not "status" in data.keys():
        data["status"] = "skipped"
        data["job_id"] = skipped_job_id

################################################################################
# Generate main test-status.json

# General Information
report: Dict[str, Any] = {}
report["repo"] = repo
report["workflow"] = repo + "/actions/runs/" + runID
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

    data["workflow_run"] = os.path.join(
        repo, "runs", data["job_id"], "?check_suite_focus=true"
    )
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
