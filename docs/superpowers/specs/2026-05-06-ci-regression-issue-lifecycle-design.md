# CI Regression Issue Lifecycle Design

## Summary

Keep a single open `ci-regression` issue as the live incident record for
package test failures on GAP `main`/`master`. The issue body should always
describe the current failing package set. The issue should be closed
automatically once the latest report for `main`/`master` contains no failing
packages.

## Scope

This change only affects the regression notifier used by
`.github/workflows/update-latest-report.yml` and its tests in `tools/tests`.
It does not change how reports are generated, how package status diffs are
computed, or how non-`main`/`master` workflows behave.

## Current Behavior

`tools/notify_ci_regressions.py` only reacts when the diff report says a new
failure appeared. In that case it creates or updates an open
`ci-regression` issue and may add a comment describing the new regression
event. If later runs still contain failures but no newly introduced failure,
the script exits without touching the issue. It also never closes the issue
when all failures disappear.

## Desired Behavior

The `ci-regression` issue should represent the current incident state for the
latest `main`/`master` report.

- If the latest report contains at least one failing package and no incident
  issue is open, create one.
- If the latest report contains at least one failing package and an incident
  issue is already open, update the issue title and body so they match the
  current failing package set.
- If the latest run introduces one or more newly failing packages compared to
  the previous report, add a comment describing that regression event.
- If the latest report contains no failing packages and an incident issue is
  open, add a short resolution comment and close the issue.
- If the latest report contains no failing packages and no incident issue is
  open, do nothing.

## Data Sources

- `test-status.json` remains the source of truth for the current package
  status set.
- `test-status-diff.json` remains the source of truth for whether the current
  run introduced new failures and therefore merits an additional comment.
- `_previous-statuses.json` remains the source used to identify which
  packages are newly failing.

The implementation must not infer current failures from the diff file alone.

## Script Changes

`tools/notify_ci_regressions.py` should be extended so that its main control
flow first computes the full list of currently failing packages, then branches
based on two facts:

1. whether an incident issue is currently open; and
2. whether the latest report still contains any failures.

The script should keep the current title format and issue label. The issue
body format may continue to list the workflow URL, report URL, report id, and
failing packages. The body content for an open issue must always reflect the
current failures, not only the newest ones.

When closing an issue, the script should post a brief comment that the latest
`main`/`master` report is fully passing and include the workflow and report
links used for resolution.

## Workflow Changes

The workflow contract does not need to change. The existing
`Notify CI regressions` step in
`.github/workflows/update-latest-report.yml` should continue to invoke the
same script with the same inputs. The behavior change should be entirely
inside the Python notifier.

## Testing

Update `tools/tests/test_notify_ci_regressions.py` to cover these cases:

- no failures and no open incident issue: no API writes;
- first failure set creates a new issue with mentions;
- existing incident issue is updated when the current failing package set
  changes, even if the diff reports no newly introduced failure;
- existing incident issue is updated and commented when new failures are
  introduced;
- existing incident issue is commented on and closed when the report becomes
  fully green.

The tests should keep using stub `Session` objects and should verify the
GitHub API methods, payloads, and resulting action summary.

## Error Handling

Retain the current `requests` error handling style: GitHub API responses
should still be checked via `raise_for_status()`. No retry logic is needed in
this change.
