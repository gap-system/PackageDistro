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

# Run this script on main branch with data and gh-pages worktree

"""
This script updates the latest symlink for the report,
and generates a html-redirect along with a badge.
"""

import json
import os
import sys
from typing import Any, Dict

from utils import error, symlink

################################################################################
# Arguments and Paths
num_args = len(sys.argv)

if num_args <= 1 or num_args > 3:
    error("Unknown number of arguments")

# relative paths to report directories from root
root = "data/reports"
os.makedirs(root, exist_ok=True)
dir_last_report_rel = "latest-master"

if num_args > 1:
    dir_report_rel = sys.argv[1]
if num_args > 2:
    dir_last_report_rel = sys.argv[2]

dir_report = os.path.join(root, dir_report_rel)

################################################################################
# Read current test-status
report_path = os.path.join(dir_report, "test-status.json")
with open(report_path, "r") as f:
    report = json.load(f)

################################################################################
# Update symlink
dir_last_report_symbolic = os.path.join(root, dir_last_report_rel)
symlink(dir_report_rel, dir_last_report_symbolic, overwrite=True)


################################################################################
# Generate html redirect
def generate_redirect(
    report: Dict[str, Any], dir_report: str, dir_last_report_rel: str
) -> None:
    dir_redirect = os.path.join("gh-pages", dir_last_report_rel)
    os.makedirs(dir_redirect, exist_ok=True)

    repo = report["repo"]
    blob_url = repo + "/blob/" + dir_report + "/report.md"

    with open(os.path.join(dir_redirect, "redirect.html"), "w") as f:
        f.write(
            f"""
        <!DOCTYPE html>
        <meta charset="utf-8">
        <title>Redirecting to latest report</title>
        <meta http-equiv="refresh" content="0; URL={blob_url}">
        <link rel="canonical" href="{blob_url}">
        </meta>
        <body>
        <a href="{blob_url}">{blob_url}</a>
        </body>
        """
        )


################################################################################
# Generate badge, see https://shields.io/endpoint
def generate_badge(report: Dict[str, Any], dir_last_report_rel: str) -> None:
    relativeFailures = report["failure"] / (report["failure"] + report["success"])
    if relativeFailures > 0.08:
        color = "critical"
    elif relativeFailures > 0:
        color = "important"
    else:
        color = "success"

    badge = {
        "schemaVersion": 1,
        "label": "Tests",
        "message": f'{report["success"]} pass, {report["failure"]} fail, {report["skipped"]} skip',
        "color": color,
        "namedLogo": "github",
    }

    dir_badge = os.path.join("data/badges", dir_last_report_rel)
    os.makedirs(dir_badge, exist_ok=True)

    with open(os.path.join(dir_badge, "badge.json"), "w") as f:
        json.dump(badge, f, ensure_ascii=False, indent=2)
        f.write("\n")


################################################################################
generate_redirect(report, dir_report, dir_last_report_rel)
generate_badge(report, dir_last_report_rel)
