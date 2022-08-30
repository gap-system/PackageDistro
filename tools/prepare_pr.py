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
This script takes the name of a single package or package group (as defined in
`group_packages.py`), followed by a list of paths to modified meta.json files.

It selects from the given list of modified meta.json files all that correspond
to the given package or group, and finally prints a list of environment
variable definitions suitable for addittion to the $GITHUB_ENV files used in
GitHub workflows to define environment variables. The data in these
definitions is used to set up a pull request by the `scan-for-updates.yml`
GitHub workflow.
"""

import random
import string
import subprocess
import sys

from typing import Any, Dict, List

import utils
import group_packages


def randomword(length: int) -> str:
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))


def infostr_for_package(pkg_json: Dict[str, Any]) -> str:
    s = f"- {pkg_json['PackageName']} {pkg_json['Version']}: "
    s += f"[[`PackageInfo.g`]({pkg_json['PackageInfoURL']})] "
    s += f"[[`README`]({pkg_json['README_URL']})] "
    s += f"[[website]({pkg_json['PackageWWWHome']})] "
    s += f"[[source archive]({utils.archive_url(pkg_json)})] "
    s += "\n"
    return s


def is_new_package(pkg_name: str) -> bool:
    fname = utils.metadata_fname(pkg_name)
    result = subprocess.run(
        ["git", "status", "--porcelain", fname], capture_output=True, encoding="UTF-8"
    )
    if result.returncode != 0:
        utils.error("git status returned an error")
    return result.stdout.startswith("?")


def main(pkg_or_group_name: str, modmap: List[str]) -> None:
    # select all entries of `modified` in the given group
    modified = [
        x for x in modmap if group_packages.name_or_group(x) == pkg_or_group_name
    ]
    if len(modified) == 0:
        utils.error(f"no modified files belong to {pkg_or_group_name}")

    # get the metadata for the first package; if it is the only one,
    # we'll use it to get the version for the PR title; if it is one
    # of multiple in a group, we can still use it to extract the common
    # source repository URL
    pkg_json = utils.metadata(modified[0])

    # generate PR title and secondary label
    if len(modified) == 1:
        version = pkg_json["Version"]
        if is_new_package(modified[0]):
            title = f"[{pkg_or_group_name}] New package, version {version}"
            label = "new package"
        else:
            title = f"[{pkg_or_group_name}] Update to {version}"
            label = "package update"
    else:
        title = f"[{pkg_or_group_name}] Updates for several packages"
        label = "package update"

    print(f"PR_TITLE={title}")
    print(f"PR_LABEL={label}")

    # list of files to be included into the PR, comma-separated, for the
    # 'add-paths' input of the create-pull-request action; see
    # https://github.com/peter-evans/create-pull-request#action-inputs
    files = map(utils.metadata_fname, modified)
    print(f"PR_FILES={','.join(files)}")

    # generate PR body content
    mod_json = map(utils.metadata, modified)
    body = "".join(map(infostr_for_package, mod_json))

    # add link to the source repository; we do this only once, as package groups
    # are defined via the source repository
    if "SourceRepository" in pkg_json:
        url = pkg_json["SourceRepository"]["URL"]
        body += f"""- [source repository]({url})""" + "\n"

    # HACK: also add the issue tracker only once; while in theory packages in
    # a group could have different issue trackers, this is not currently the case,
    # ever. We'll deal with it if it ever happens
    if "IssueTrackerURL" in pkg_json:
        body += f"""- [issue tracker]({pkg_json["IssueTrackerURL"]})""" + "\n"

    # generate multiline environment variable using "heredoc" syntax, as per
    # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#multiline-strings
    # we use a random delimiter for security reasons, to avoid injection attacks
    delim = randomword(10)
    print(f"PR_BODY<<{delim}")
    print(body)
    print(delim)


if __name__ == "__main__":
    main(sys.argv[1], [utils.normalize_pkg_name(x) for x in sys.argv[2:]])
