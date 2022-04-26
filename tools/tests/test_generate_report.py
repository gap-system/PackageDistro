# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, missing-function-docstring
# pylint: disable=missing-class-docstring, invalid-name, redefined-outer-name

"""
This module contains some tests for the generate_report.py script
"""

import os
import shutil

# Copy {file} from {root}/tools/tests/_data/{id} into directory {root}/data/{id}
# Returns destination folder of copied file
def copy_files(root, id, file):
    dst = os.path.join(root, "data", "reports", id)
    os.makedirs(dst, exist_ok=True)
    shutil.copyfile(
        os.path.join(root, "tools/tests/_data", id, file), os.path.join(dst, file)
    )
    return dst


def clear_files(root):
    shutil.rmtree(os.path.join(root, "data", "reports", "test_reports"))
    # {root}/data/reports is empty
    path = os.path.join(root, "data", "reports")
    if not any(os.scandir(path)):
        os.rmdir(path)
    # {root}/data is empty
    path = os.path.join(root, "data")
    if not any(os.scandir(path)):
        os.rmdir(path)


def generate_report(root):
    previous_id = "test_reports/previous"
    current_id = "test_reports/current"
    correct_id = "test_reports/correct"

    previous_path = copy_files(root, previous_id, "test-status.json")
    current_path = copy_files(root, current_id, "test-status.json")
    correct_path = copy_files(root, correct_id, "report.md")

    os.system(f"python tools/generate_report.py {current_id} {previous_id}")

    return correct_path, current_path


def test_report():
    root = "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-2])
    os.chdir(root)

    correct_path, current_path = generate_report(root)

    # It exits with 1 if there were differences and 0 means no differences.
    assert (
        os.system(
            f"git diff --no-index --color {correct_path}/report.md {current_path}/report.md"
        )
        == 0
    )

    clear_files(root)
