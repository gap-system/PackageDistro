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

from utils import error, warning

import sys
import os
import glob
import json
from datetime import datetime

from typing import Any, Dict

################################################################################
# Arguments
num_args = len(sys.argv)

if num_args > 5:
    error('Too many arguments')

repo = runID = hash = which_gap = 'Unknown'

if num_args > 1: repo = 'https://github.com/'+sys.argv[1]
if num_args > 2: runID = sys.argv[2]
if num_args > 3: hash = sys.argv[3]
if num_args > 4: which_gap = sys.argv[4]

################################################################################
# Collect the job-status of each package from _reports/
files = []
for file in glob.glob('_reports/**/*.json', recursive=True):
    files.append(file)

files.sort()

pkgs = {}

for file in files:
    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)

    pkgs[os.path.splitext(os.path.basename(file))[0]] = data

################################################################################
# Generate main test-status.json

# General Information
report: Dict[str,Any] = {}
report['repo'] = repo
report['workflow'] = repo+'/actions/runs/'+runID
report['hash'] = hash
date = str(datetime.now()).split('.')[0]
report['date'] = date
report['id'] = os.path.join(which_gap, "%s-%s" % (date.replace(' ','-'), hash[:8]))

# Path
root = 'data/reports'
dir_test_status = os.path.join(root, report['id'])
os.makedirs(dir_test_status, exist_ok = True)

# Package Information
for pkg, data in pkgs.items():
    with open(os.path.join('packages', pkg, 'meta.json'), 'r') as f:
        meta = json.load(f)

    data['version'] = meta['Version']
    data['archive_url'] = meta['ArchiveURL']
    data['archive_sha256'] = meta['ArchiveSHA256']

    # Get maximum of each status via the hierarchy 'failure' > 'cancelled' = 'skipped' > 'success'.
    # For safety, check if status is always known.
    status_list = [value for key, value in data.items() if key.startswith('status_')]
    unknown_status_list = [status for status in status_list if not status in ['failure', 'cancelled', 'skipped', 'success']]
    if len(unknown_status_list) > 0:
        data['status'] = 'unknown'
    elif 'failure' in status_list:
        data['status'] = 'failure'
    elif 'cancelled' in status_list or 'skipped' in status_list:
        data['status'] = 'skipped'
    else: # all are 'success'
        data['status'] = 'success'

report['pkgs'] = pkgs

# Summary Information
report['total'] = 0
report['success'] = 0
report['failure'] = 0
report['skipped'] = 0

for pkg, data in pkgs.items():
    report['total'] += 1
    status = data['status']
    if status == 'success':
        report['success'] += 1
    elif status == 'failure':
        report['failure'] += 1
    elif status == 'skipped':
        report['skipped'] += 1
    else:
        warning('Unknown job status detected for pkg \"'+pkg+'\"')

with open(os.path.join(dir_test_status, 'test-status.json'), 'w') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(report['id'])
