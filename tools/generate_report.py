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
This script compares the current test-status.json with a previous version,
generates a main report.md along with
    a test-status-diff.json,
    a html-redirect, and
    a badge.
"""

from utils import warning, error, symlink, string_to_bool

import sys
import os
import json

################################################################################
# Arguments and Paths
num_args = len(sys.argv)

if num_args <= 1 or num_args > 4:
    error('Unknown number of arguments')

# relative paths to report directories from root
root = 'data/reports'
os.makedirs(root, exist_ok = True)
dir_last_report_rel = 'latest'
override_last = True

if num_args > 1: dir_report_rel = sys.argv[1]
if num_args > 2: dir_last_report_rel = sys.argv[2]
if num_args > 3: override_last = string_to_bool(sys.argv[3])

dir_report = os.path.realpath(os.path.join(root, dir_report_rel))
dir_last_report_symbolic = os.path.join(root, dir_last_report_rel)
dir_last_report = os.path.realpath(dir_last_report_symbolic)

report_path = os.path.join(dir_report, 'test-status.json')
last_report_path = os.path.join(dir_last_report, 'test-status.json')

if override_last:
    dir_badge = os.path.join('data/badges', dir_last_report_rel)
    os.makedirs(dir_badge, exist_ok = True)

    dir_redirect = os.path.join('gh-pages', dir_last_report_rel)
    os.makedirs(dir_redirect, exist_ok = True)

################################################################################
# Read current and previous test-status
with open(report_path, 'r') as f:
    report = json.load(f)

if os.path.isfile(last_report_path):
    with open(last_report_path, 'r') as f:
        last_report = json.load(f)
else: # deal with the first run of this script
    last_report = {'pkgs': {}, 'hash': 'Unknown', 'id': 'NULL'}

repo = report['repo']

################################################################################
# Generate report.md and test-status-diff.json
report_diff = {}
report_diff['current'] = report['id']
report_diff['last'] = last_report['id']
report_diff['total'] = report['total']
report_diff['failure'] = report['failure']
report_diff['success'] = report['success']
report_diff['skipped'] = report['skipped']

with open(dir_report+'/report.md', 'w') as f:
    # Header
    f.write('# Package Evaluation Report\n\n')
    f.write('## Job Properties\n\n')
    f.write('*Testing:* [%s](%s) vs [%s](%s)\n\n' % (
        report_diff['current'],
        os.path.join(repo, 'blob', root, report_diff['current']),
        report_diff['last'],
        os.path.join(repo, 'blob', root, report_diff['last'])
        ))
    f.write('*Generated by Workflow:* %s\n\n' % report['workflow'])
    f.write('In total, %d packages were tested, out of which %d succeeded, %d failed and %d were skipped.\n\n' % (report['total'], report['success'], report['failure'], report['skipped']))

    pkgs = report['pkgs']
    last_pkgs = last_report['pkgs']

    ############################################################################
    # New Packages
    pkgs_new = pkgs.keys() - last_pkgs.keys()

    report_diff['new'] = len(pkgs_new)
    if len(pkgs_new) > 0:
        f.write('## New Packages\n\n')
        for pkg in pkgs_new:
            status = pkgs[pkg]['status']
            f.write('- %s : %s <br>\n' % (pkg, status))

    ############################################################################
    # Removed Packages
    pkgs_removed = last_pkgs.keys() - pkgs.keys()

    report_diff['removed'] = len(pkgs_removed)
    if len(pkgs_removed) > 0:
        f.write('## Removed Packages\n\n')
        for pkg in pkgs_removed:
            status = last_pkgs[pkg]['status']
            f.write('- %s : %s <br>\n' % (pkg, status))

    ############################################################################
    # Changed Status Packages
    for status, status_msg, status_header in [
                ('failure', 'failed', ':exclamation: Packages now failing'),
                ('success', 'succeeded', ':heavy_check_mark: Packages now succeeding'),
                ('skipped', 'skipped', ':heavy_multiplication_x: Packages that now skipped')]:
        pkgs_filtered = [pkg for pkg in pkgs.keys() if
            pkg in last_pkgs.keys() and
            pkgs[pkg]['status'] != last_pkgs[pkg]['status'] and
            pkgs[pkg]['status'] == status]

        report_diff[status+'_changed'] = len(pkgs_filtered)
        if len(pkgs_filtered) > 0:
            f.write('## %s\n\n' % status_header)
            f.write('%d package(s) %s tests only on the current version.' % (len(pkgs_filtered), status_msg))
            f.write('<details> <summary>Click to expand!</summary>\n\n')
            for pkg in pkgs_filtered:
                version = pkgs[pkg]['version']
                last_status = last_pkgs[pkg]['status']
                last_version = last_pkgs[pkg]['version']
                f.write('- %s %s vs %s %s (%s) <br>\n' % (pkg, version, pkg, last_version, last_status))
            f.write('</details>\n\n')

    ############################################################################
    # Same Status Packages
    for status, status_msg, status_header in [
                ('failure', 'failed', ':exclamation: Packages still failing'),
                ('success', 'succeeded', ':heavy_check_mark: Packages still succeeding'),
                ('skipped', 'skipped', ':heavy_minus_sign: Packages that still skipped')]:
        pkgs_filtered = [pkg for pkg in pkgs.keys() if
            pkg in last_pkgs.keys() and
            pkgs[pkg]['status'] == last_pkgs[pkg]['status'] and
            pkgs[pkg]['status'] == status]

        report_diff[status+'_same'] = len(pkgs_filtered)
        if len(pkgs_filtered) > 0:
            f.write('## %s\n\n' % status_header)
            f.write('%d package(s) %s tests also on the previous version.' % (len(pkgs_filtered), status_msg))
            f.write('<details> <summary>Click to expand!</summary>\n\n')
            for pkg in pkgs_filtered:
                version = pkgs[pkg]['version']
                f.write('- %s %s <br>\n' % (pkg, version))
            f.write('</details>\n\n')

# Write test-status-diff.json
with open(dir_report+'/test-status-diff.json', 'w') as f:
    json.dump(report_diff, f, ensure_ascii=False, indent=2)

################################################################################
# Update Latest
if override_last:
    symlink(dir_report, dir_last_report_symbolic, overwrite=True)

    ############################################################################
    # Generate html redirect
    with open(os.path.join(dir_redirect, 'redirect.html'), 'w') as f:
        f.write('''
        <!DOCTYPE html>
        <meta charset="utf-8">
        <title>Redirecting to latest report</title>
        <meta http-equiv="refresh" content="0; URL=%s">
        <link rel="canonical" href="%s">
        ''' % (repo+'/blob/'+dir_report+'/report.md', repo+'/'+dir_report+'/report.md'))

    ############################################################################
    # Generate badge
    relativeFailures = 1 - report['success'] / report['total']
    if relativeFailures > 0.05:
        color = 'critical'
    elif relativeFailures > 0:
        color = 'important'
    else:
        color = 'success'

    badge = {
        'schemaVersion' : 1,
        'label': 'Tests',
        'message': '%d/%d passing' % (report['success'], report['total']),
        'color': color,
        'namedLogo': "github"
    }

    with open(os.path.join(dir_badge, 'badge.json'), 'w') as f:
        json.dump(badge, f, ensure_ascii=False, indent=2)
