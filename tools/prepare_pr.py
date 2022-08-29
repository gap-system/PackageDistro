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
This script takes the name of a single package or
package group (as defined in `group_packages.py`), followed
by a list of paths to modified meta.json files.

It selects from the given list of modified meta.json files all that
correspond to the given package or group, and finally prints a list
of environment variable definitions suitable for addittion to
the $GITHUB_ENV files used in GitHub workflows to define environment
variables. The data in these definitions is used to set up a pull request
by the `scan-for-updates.yml` GitHub workflow.
"""

import random
import string
import sys
import textwrap

from typing import Any, Dict, List

import utils
import group_packages


def randomword(length):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))


def infostr_for_package(pkg_json: Dict[str, Any]) -> str:
    s = textwrap.dedent(
        f"""\
        Relevant links for {pkg_json['PackageName']} {pkg_json['Version']}:
        - [website]({pkg_json["PackageWWWHome"]})
        - [`PackageInfo.g`]({pkg_json["PackageInfoURL"]})
        - [`README`]({pkg_json["README_URL"]})
        - [source archive]({utils.archive_url(pkg_json)})
        """
    )
    if "IssueTrackerURL" in pkg_json:
        s += f"""- [issue tracker]({pkg_json["IssueTrackerURL"]})""" + "\n"
    # TODO: for groups, we only need to print the source repository once...
    if "SourceRepository" in pkg_json:
        s += f"""- [source repository]({pkg_json["SourceRepository"]["URL"]})""" + "\n"
    return s


def is_new_package(pkg_name: str) -> bool:
    utils.warning(f"TODO: check if {pkg_name} is new")
    # git ls-files | fgrep -q packages/${{ matrix.package }}/meta.json
    return False


def main(pkg_or_group_name: str, modified: List[str]) -> None:
    # select all entries of `modified` in the given group
    modified = [
        x for x in modified if group_packages.name_or_group(x) == pkg_or_group_name
    ]
    if len(modified) == 0:
        utils.error(f"no modified files belong to {pkg_or_group_name}")

    mod_json = map(utils.metadata, modified)
    body = "\n".join(map(infostr_for_package, mod_json))
    if len(modified) == 1:
        pkg_json = utils.metadata(modified[0])
        version = pkg_json["Version"]
        if is_new_package(modified[0]):
            title = f"[{pkg_or_group_name}] New package, version {version}"
            label = "new package"
        else:
            title = f"[{pkg_or_group_name}] Update to version {version}"
            label = "package update"
    else:
        title = f"[{pkg_or_group_name}] Updates"
        label = "package update"

    print(f"PR_TITLE={title}")
    print(f"PR_LABEL={label}")

    # generate multiline environment variable using "heredoc" syntax, as per
    # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#multiline-strings
    # we use a random delimiter for security reasons, to avoid injection attacks
    delim = randomword(10)
    print(f"PR_BODY<<{delim}")
    print(body)
    print(delim)


if __name__ == "__main__":
    main(sys.argv[1], map(utils.normalize_pkg_name, sys.argv[2:]))
