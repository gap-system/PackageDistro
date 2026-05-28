# pylint: disable=missing-function-docstring

import os
import sys

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)

import gather_dependencies


def test_metadata_ubuntu_packages_extracts_ubuntu_entries():
    assert gather_dependencies.metadata_ubuntu_packages(
        {
            "Dependencies": {
                "NeededSystemPackages": {
                    "Homebrew": [["ignored"]],
                    "Ubuntu": [["dynamic-dev"], ["dynamic-runtime"]],
                }
            }
        }
    ) == {"dynamic-dev", "dynamic-runtime"}


def test_metadata_ubuntu_packages_handles_missing_field():
    assert gather_dependencies.metadata_ubuntu_packages({"Dependencies": {}}) == set()


def test_gather_dependencies_uses_needed_system_packages(monkeypatch):
    metadata = {
        "root": {
            "Dependencies": {
                "NeededOtherPackages": [],
                "NeededSystemPackages": {
                    "Ubuntu": [["dynamic-dev"], ["dynamic-runtime"]]
                },
                "SuggestedOtherPackages": [],
            }
        }
    }

    monkeypatch.setattr(gather_dependencies, "metadata", metadata.__getitem__)
    monkeypatch.setattr(gather_dependencies, "ubtunu_deps", {"root": ["legacy-dev"]})

    assert gather_dependencies.gather_dependencies("root", set()) == {
        "dynamic-dev",
        "dynamic-runtime",
        "legacy-dev",
    }


def test_gather_dependencies_falls_back_to_legacy_table(monkeypatch):
    metadata = {
        "root": {
            "Dependencies": {
                "NeededOtherPackages": [],
                "SuggestedOtherPackages": [],
            }
        }
    }

    monkeypatch.setattr(gather_dependencies, "metadata", metadata.__getitem__)
    monkeypatch.setattr(gather_dependencies, "ubtunu_deps", {"root": ["legacy-dev"]})

    assert gather_dependencies.gather_dependencies("root", set()) == {"legacy-dev"}
