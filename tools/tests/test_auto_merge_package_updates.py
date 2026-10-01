# -*- coding: utf-8 -*-

import importlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def head_commit(date="2026-05-20T00:00:00Z"):
    return json.dumps({"commit": {"committer": {"date": date}}})


def label(name):
    return {"name": name}


def pr(number, **overrides):
    data = {
        "number": number,
        "title": f"Update package {number}",
        "url": f"https://github.com/gap-system/PackageDistro/pull/{number}",
        "createdAt": "2026-05-20T00:00:00Z",
        "headRefName": f"automatic/pkg{number}",
        "headRefOid": f"sha{number}",
        "headRepositoryOwner": {"login": "gap-system"},
        "isDraft": False,
        "labels": [label("automated pr"), label("package update")],
    }
    data.update(overrides)
    return data


def test_filters_package_update_candidates_by_source_labels_and_age():
    module = importlib.import_module("auto_merge_package_updates")

    candidates = module.filter_candidate_pull_requests(
        [
            pr(1),
            pr(2, labels=[label("automated pr"), label("new package")]),
            pr(3, headRefName="manual/pkg3"),
            pr(4, headRepositoryOwner={"login": "someone-else"}),
            pr(5, isDraft=True),
            pr(6, createdAt="2026-05-21T23:30:00Z"),
        ],
        repository_owner="gap-system",
        minimum_age_seconds=86400,
        now=module.parse_github_datetime("2026-05-22T02:00:00Z"),
    )

    assert [candidate["number"] for candidate in candidates] == [1]


def test_dry_run_prints_merge_candidates_without_merging(capsys):
    module = importlib.import_module("auto_merge_package_updates")

    calls = []

    def fake_run_gh(args):
        calls.append(args)
        if args[:2] == ["pr", "list"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=json.dumps([pr(1)]),
                stderr="",
            )
        if args[:2] == ["api", "repos/gap-system/PackageDistro/commits/sha1"]:
            return subprocess.CompletedProcess(args, 0, stdout=head_commit(), stderr="")
        if args[:2] == ["api", "repos/gap-system/PackageDistro/issues/1/comments"]:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        if args[:2] == ["api", "repos/gap-system/PackageDistro/pulls/1/reviews"]:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        if args[:3] == ["pr", "checks", "1"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=json.dumps(
                    [
                        {
                            "name": "Package tests passed",
                            "bucket": "pass",
                            "state": "SUCCESS",
                        }
                    ]
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected gh call: {args}")

    merged = module.auto_merge_package_updates(
        repository="gap-system/PackageDistro",
        repository_owner="gap-system",
        minimum_age_seconds=86400,
        dry_run=True,
        now=module.parse_github_datetime("2026-05-22T02:00:00Z"),
        run_gh=fake_run_gh,
    )

    out = capsys.readouterr().out
    assert merged == [1]
    assert "Would merge PR #1" in out
    assert not any(call[:3] == ["pr", "merge", "1"] for call in calls)


def test_human_comment_blocks_auto_merge_unless_marked_noblock(capsys):
    module = importlib.import_module("auto_merge_package_updates")

    calls = []

    def fake_run_gh(args):
        calls.append(args)
        if args[:2] == ["pr", "list"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=json.dumps([pr(1), pr(2)]),
                stderr="",
            )
        if args[:2] == ["api", "repos/gap-system/PackageDistro/commits/sha1"]:
            return subprocess.CompletedProcess(args, 0, stdout=head_commit(), stderr="")
        if args[:2] == ["api", "repos/gap-system/PackageDistro/issues/1/comments"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=json.dumps(
                    [
                        {
                            "body": "Please hold this update.",
                            "html_url": "https://example.com/comment/1",
                            "user": {"login": "pkg-author", "type": "User"},
                        }
                    ]
                ),
                stderr="",
            )
        if args[:2] == ["api", "repos/gap-system/PackageDistro/commits/sha2"]:
            return subprocess.CompletedProcess(args, 0, stdout=head_commit(), stderr="")
        if args[:2] == ["api", "repos/gap-system/PackageDistro/issues/2/comments"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=json.dumps(
                    [
                        {
                            "body": "Package Evaluation Report",
                            "html_url": "https://example.com/comment/2",
                            "user": {
                                "login": "gap-package-distribution-bot[bot]",
                                "type": "Bot",
                            },
                        },
                        {
                            "body": "Looks fine to me. [noblock]",
                            "html_url": "https://example.com/comment/3",
                            "user": {"login": "maintainer", "type": "User"},
                        },
                    ]
                ),
                stderr="",
            )
        if args[:2] == ["api", "repos/gap-system/PackageDistro/pulls/2/reviews"]:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        if args[:3] == ["pr", "checks", "2"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=json.dumps(
                    [
                        {
                            "name": "Package tests passed",
                            "bucket": "pass",
                            "state": "SUCCESS",
                        }
                    ]
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected gh call: {args}")

    merged = module.auto_merge_package_updates(
        repository="gap-system/PackageDistro",
        repository_owner="gap-system",
        minimum_age_seconds=86400,
        dry_run=True,
        now=module.parse_github_datetime("2026-05-22T02:00:00Z"),
        run_gh=fake_run_gh,
    )

    out = capsys.readouterr().out
    assert merged == [2]
    assert "PR #1 has blocking comments" in out
    assert "Would merge PR #2" in out


def test_comment_read_failure_exits_instead_of_blocking_silently():
    module = importlib.import_module("auto_merge_package_updates")

    def fake_run_gh(args):
        if args[:2] == ["api", "repos/gap-system/PackageDistro/commits/sha1"]:
            return subprocess.CompletedProcess(args, 0, stdout=head_commit(), stderr="")
        if args[:2] == ["api", "repos/gap-system/PackageDistro/issues/1/comments"]:
            return subprocess.CompletedProcess(
                args,
                1,
                stdout="",
                stderr="permission denied",
            )
        raise AssertionError(f"unexpected gh call: {args}")

    try:
        module.list_issue_comments("gap-system/PackageDistro", 1, fake_run_gh)
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("expected SystemExit")


def test_merge_failure_exits_instead_of_returning_false():
    module = importlib.import_module("auto_merge_package_updates")

    def fake_run_gh(args):
        if args[:3] == ["pr", "merge", "1"]:
            return subprocess.CompletedProcess(
                args,
                1,
                stdout="",
                stderr="head branch changed",
            )
        raise AssertionError(f"unexpected gh call: {args}")

    try:
        module.merge_pull_request(pr(1), fake_run_gh)
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("expected SystemExit")


def review(login, state, body="", user_type="User"):
    return {
        "body": body,
        "state": state,
        "html_url": f"https://example.com/review/{login}",
        "user": {"login": login, "type": user_type},
    }


def test_blocking_reviews():
    module = importlib.import_module("auto_merge_package_updates")

    reviews = [
        # change request withdrawn by a later approval
        review("alice", "CHANGES_REQUESTED", "Please fix."),
        review("alice", "APPROVED"),
        # a later comment does not withdraw a change request
        review("bob", "CHANGES_REQUESTED"),
        review("bob", "COMMENTED", "Still waiting. [noblock]"),
        review("carol", "CHANGES_REQUESTED"),
        review("carol", "DISMISSED"),
        review("dave", "COMMENTED", "Is this right?"),
        review("erin", "COMMENTED", "Fine. [noblock]"),
        review("bot[bot]", "CHANGES_REQUESTED", user_type="Bot"),
    ]

    blockers = module.blocking_reviews(reviews)

    assert [(r["user"]["login"], r["state"]) for r in blockers] == [
        ("bob", "CHANGES_REQUESTED"),
        ("dave", "COMMENTED"),
    ]


def test_requested_changes_block_auto_merge(capsys):
    module = importlib.import_module("auto_merge_package_updates")

    def fake_run_gh(args):
        if args[:2] == ["pr", "list"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps([pr(1)]), stderr=""
            )
        if args[:2] == ["api", "repos/gap-system/PackageDistro/commits/sha1"]:
            return subprocess.CompletedProcess(args, 0, stdout=head_commit(), stderr="")
        if args[:2] == ["api", "repos/gap-system/PackageDistro/issues/1/comments"]:
            return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")
        if args[:2] == ["api", "repos/gap-system/PackageDistro/pulls/1/reviews"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=json.dumps([[review("maintainer", "CHANGES_REQUESTED")]]),
                stderr="",
            )
        raise AssertionError(f"unexpected gh call: {args}")

    merged = module.auto_merge_package_updates(
        repository="gap-system/PackageDistro",
        repository_owner="gap-system",
        minimum_age_seconds=86400,
        dry_run=True,
        now=module.parse_github_datetime("2026-05-22T02:00:00Z"),
        run_gh=fake_run_gh,
    )

    out = capsys.readouterr().out
    assert merged == []
    assert "PR #1 has blocking reviews" in out


def test_missing_gate_check_blocks_auto_merge(capsys):
    module = importlib.import_module("auto_merge_package_updates")

    def fake_run_gh(args):
        if args[:3] == ["pr", "checks", "1"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=json.dumps(
                    [
                        {
                            "name": "Detect affected packages",
                            "bucket": "pass",
                            "state": "SUCCESS",
                        }
                    ]
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected gh call: {args}")

    assert not module.required_checks_pass(1, fake_run_gh)
    assert "Package tests passed" in capsys.readouterr().out


def test_recent_push_delays_auto_merge(capsys):
    module = importlib.import_module("auto_merge_package_updates")

    def fake_run_gh(args):
        if args[:2] == ["pr", "list"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps([pr(1)]), stderr=""
            )
        if args[:2] == ["api", "repos/gap-system/PackageDistro/commits/sha1"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=head_commit("2026-05-21T23:30:00Z"), stderr=""
            )
        raise AssertionError(f"unexpected gh call: {args}")

    merged = module.auto_merge_package_updates(
        repository="gap-system/PackageDistro",
        repository_owner="gap-system",
        minimum_age_seconds=86400,
        dry_run=True,
        now=module.parse_github_datetime("2026-05-22T02:00:00Z"),
        run_gh=fake_run_gh,
    )

    assert merged == []
    assert "PR #1 was updated too recently" in capsys.readouterr().out
