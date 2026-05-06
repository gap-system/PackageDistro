# CI Regression Issue Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the CI regression notifier keep one live incident issue in sync with the current failing package set and close it automatically once the latest `master` report is fully green.

**Architecture:** Extend `tools/notify_ci_regressions.py` so it computes both the current failing package set and the newly introduced failing package set, then routes create, update, comment, close, and no-op behavior through one control flow. Keep the GitHub Actions workflow interface unchanged and drive the behavior with focused tests in `tools/tests/test_notify_ci_regressions.py`.

**Tech Stack:** Python 3, `requests`, `pytest`, GitHub Issues REST API

---

### Task 1: Cover persistent issue updates in tests

**Files:**
- Modify: `tools/tests/test_notify_ci_regressions.py`
- Modify: `tools/notify_ci_regressions.py`
- Test: `tools/tests/test_notify_ci_regressions.py`

- [ ] **Step 1: Write the failing test for updating an existing issue when failures persist but no new regression was introduced**

```python
def test_run_updates_existing_incident_for_current_failures_without_comment():
    module = importlib.import_module("notify_ci_regressions")
    seen = {"patches": [], "posts": []}

    class Response:
        def __init__(self, payload):
            self.payload = payload
            self.links = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def get(self, url, headers=None, params=None):
            return Response(
                [
                    {
                        "number": 7550,
                        "title": "CI regression: packages now failing on GAP master",
                        "labels": [{"name": "ci-regression"}],
                    }
                ]
            )

        def post(self, url, headers=None, json=None):
            seen["posts"].append((url, json))
            raise AssertionError("post should not be called")

        def patch(self, url, headers=None, json=None):
            seen["patches"].append((url, json))
            return Response({"number": 7550})

    result = module.run_notification(
        session=Session(),
        repo="gap-system/PackageDistro",
        token="TOKEN",
        which_gap="master",
        mentions=["@user1", "@user2"],
        test_status={
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/10",
            "id": "master/2026-04-25-fedcba98",
            "pkgs": {
                "atlasrep": {
                    "status": "failure",
                    "version": "2.1",
                    "workflow_run": "https://example.invalid/job/atlasrep",
                },
                "guava": {
                    "status": "failure",
                    "version": "3.0",
                    "workflow_run": "https://example.invalid/job/guava",
                },
            },
        },
        report_diff={"failure_changed": 0},
        previous_statuses={"atlasrep": "failure", "guava": "failure"},
        report_url="https://github.com/gap-system/PackageDistro/blob/data/reports/master/report.md",
    )

    assert result == {"action": "updated", "issue_number": 7550}
    assert len(seen["patches"]) == 1
    assert "atlasrep 2.1" in seen["patches"][0][1]["body"]
    assert "guava 3.0" in seen["patches"][0][1]["body"]
    assert seen["posts"] == []
```

- [ ] **Step 2: Run the new test and verify it fails against the current notifier**

Run: `python -m pytest tools/tests/test_notify_ci_regressions.py -k current_failures_without_comment -vv`
Expected: FAIL because `run_notification` currently returns `{"action": "noop", "issue_number": None}` when `failure_changed` is `0`.

- [ ] **Step 3: Implement current-failure tracking and unconditional issue body refresh when failures remain**

```python
def current_failures(test_status: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for pkg, data in sorted(test_status["pkgs"].items()):
        if data["status"] == "failure":
            rows.append(
                {
                    "name": pkg,
                    "version": data["version"],
                    "job_url": data["workflow_run"],
                }
            )
    return rows


def run_notification(
    session: requests.Session,
    repo: str,
    token: str,
    which_gap: str,
    mentions: list[str],
    test_status: dict[str, Any],
    report_diff: dict[str, Any],
    previous_statuses: dict[str, str] | None = None,
    report_url: str | None = None,
) -> dict[str, Any]:
    current_rows = current_failures(test_status)
    changed_rows = changed_failures(test_status, previous_statuses or {})
    workflow_url = test_status["workflow"]
    issue = find_open_incident_issue(session, repo, token)
    title = f"{ISSUE_TITLE_PREFIX} packages now failing on GAP {which_gap}"

    if not current_rows:
        return {"action": "noop", "issue_number": None}

    body = render_issue_body(
        which_gap,
        workflow_url,
        report_url or workflow_url,
        test_status["id"],
        current_rows,
        mentions if issue is None else None,
    )

    if issue is None:
        res = session.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers=github_headers(token),
            json={"title": title, "labels": [ISSUE_LABEL], "body": body},
        )
        res.raise_for_status()
        created = res.json()
        return {"action": "created", "issue_number": created["number"]}

    session.patch(
        f"https://api.github.com/repos/{repo}/issues/{issue['number']}",
        headers=github_headers(token),
        json={"title": title, "body": body},
    ).raise_for_status()

    if changed_rows:
        session.post(
            f"https://api.github.com/repos/{repo}/issues/{issue['number']}/comments",
            headers=github_headers(token),
            json={
                "body": render_issue_comment(
                    which_gap,
                    workflow_url,
                    report_url or workflow_url,
                    test_status["id"],
                    changed_rows,
                )
            },
        ).raise_for_status()

    return {"action": "updated", "issue_number": issue["number"]}
```

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `python -m pytest tools/tests/test_notify_ci_regressions.py -k current_failures_without_comment -vv`
Expected: PASS

- [ ] **Step 5: Commit the progress**

```bash
git add tools/tests/test_notify_ci_regressions.py tools/notify_ci_regressions.py
git commit -m "ci: keep regression issue current" -m "Update the open CI regression issue whenever failures remain on GAP master, even when the latest run introduced no new failures." -m "This keeps the incident issue body aligned with the current failing package set instead of leaving stale package lists behind." -m "AI-assisted by Codex for implementation planning and code changes." -m "Co-authored-by: Codex <codex@openai.com>"
```

### Task 2: Cover comments for newly introduced failures and preserve current-body semantics

**Files:**
- Modify: `tools/tests/test_notify_ci_regressions.py`
- Modify: `tools/notify_ci_regressions.py`
- Test: `tools/tests/test_notify_ci_regressions.py`

- [ ] **Step 1: Adjust the existing update test so it proves both current-body refresh and new-regression commenting**

```python
def test_run_updates_existing_incident_and_comments_without_mentions():
    module = importlib.import_module("notify_ci_regressions")
    seen = {"patches": [], "posts": []}

    class Response:
        def __init__(self, payload):
            self.payload = payload
            self.links = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def get(self, url, headers=None, params=None):
            return Response(
                [
                    {
                        "number": 7550,
                        "title": "CI regression: packages now failing on GAP master",
                        "labels": [{"name": "ci-regression"}],
                    }
                ]
            )

        def post(self, url, headers=None, json=None):
            seen["posts"].append((url, json))
            return Response({"id": 1})

        def patch(self, url, headers=None, json=None):
            seen["patches"].append((url, json))
            return Response({"number": 7550})

    result = module.run_notification(
        session=Session(),
        repo="gap-system/PackageDistro",
        token="TOKEN",
        which_gap="master",
        mentions=["@user1", "@user2"],
        test_status={
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/10",
            "id": "master/2026-04-25-fedcba98",
            "pkgs": {
                "atlasrep": {
                    "status": "failure",
                    "version": "2.1",
                    "workflow_run": "https://example.invalid/job/atlasrep",
                },
                "guava": {
                    "status": "failure",
                    "version": "3.0",
                    "workflow_run": "https://example.invalid/job/guava",
                },
            },
        },
        report_diff={"failure_changed": 1},
        previous_statuses={"atlasrep": "failure", "guava": "success"},
        report_url="https://github.com/gap-system/PackageDistro/blob/data/reports/master/report.md",
    )

    assert result == {"action": "updated", "issue_number": 7550}
    assert "atlasrep 2.1" in seen["patches"][0][1]["body"]
    assert "guava 3.0" in seen["patches"][0][1]["body"]
    assert "guava 3.0" in seen["posts"][0][1]["body"]
    assert "@user1" not in seen["patches"][0][1]["body"]
    assert "@user1" not in seen["posts"][0][1]["body"]
```

- [ ] **Step 2: Run the focused tests and verify the updated expectations fail if the notifier still writes only newly failing packages into the issue body**

Run: `python -m pytest tools/tests/test_notify_ci_regressions.py -k "updates_existing_incident" -vv`
Expected: FAIL until the issue body uses the full current failing package set while the comment continues to describe only the newly introduced failures.

- [ ] **Step 3: Update body/comment rendering so the issue body lists all current failures and the comment lists only newly introduced failures**

```python
def render_issue_body(
    which_gap: str,
    workflow_url: str,
    report_url: str,
    report_id: str,
    rows: list[dict[str, str]],
    mentions: list[str] | None = None,
) -> str:
    body = (
        f"Current package failures on GAP `{which_gap}`.\n\n"
        f"Report id: `{report_id}`\n\n"
        f"Workflow: {workflow_url}\n\n"
        f"Report: {report_url}\n\n"
        f"Current failures:\n{format_package_lines(rows)}\n\n"
    )
    if mentions:
        body += f"{' '.join(mentions)}\n"
    return body


def render_issue_comment(...):
    return (
        f"New regression event detected on GAP `{which_gap}`.\n\n"
        f"Report id: `{report_id}`\n\n"
        f"Workflow: {workflow_url}\n\n"
        f"Report: {report_url}\n\n"
        f"New failures:\n{format_package_lines(rows)}\n"
    )
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `python -m pytest tools/tests/test_notify_ci_regressions.py -k "updates_existing_incident" -vv`
Expected: PASS

- [ ] **Step 5: Commit the progress**

```bash
git add tools/tests/test_notify_ci_regressions.py tools/notify_ci_regressions.py
git commit -m "ci: separate current and new failures" -m "Render the regression issue body from the full current failing package set while keeping update comments scoped to newly introduced failures." -m "This preserves incident history in comments without making the live issue description drift from the latest report." -m "AI-assisted by Codex for implementation planning and code changes." -m "Co-authored-by: Codex <codex@openai.com>"
```

### Task 3: Close the incident issue when the latest report is fully green

**Files:**
- Modify: `tools/tests/test_notify_ci_regressions.py`
- Modify: `tools/notify_ci_regressions.py`
- Test: `tools/tests/test_notify_ci_regressions.py`

- [ ] **Step 1: Write the failing tests for the green-report cases**

```python
def test_run_returns_without_api_calls_when_no_failures_and_no_issue():
    module = importlib.import_module("notify_ci_regressions")
    calls = []

    class Response:
        def __init__(self, payload):
            self.payload = payload
            self.links = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def get(self, url, headers=None, params=None):
            calls.append(("get", url, params))
            return Response([])

        def post(self, *args, **kwargs):
            calls.append(("post", args, kwargs))
            raise AssertionError("GitHub API should not be queried")

        def patch(self, *args, **kwargs):
            calls.append(("patch", args, kwargs))
            raise AssertionError("GitHub API should not be queried")

    result = module.run_notification(
        session=Session(),
        repo="gap-system/PackageDistro",
        token="TOKEN",
        which_gap="master",
        mentions=["@user1", "@user2"],
        test_status={
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/1",
            "id": "master/2026-04-24-abcdef12",
            "pkgs": {
                "atlasrep": {
                    "status": "success",
                    "version": "2.1",
                    "workflow_run": "https://example.invalid/job/atlasrep",
                }
            },
        },
        report_diff={"failure_changed": 0},
    )

    assert result == {"action": "noop", "issue_number": None}
    assert calls == [
        (
            "get",
            "https://api.github.com/repos/gap-system/PackageDistro/issues",
            {"state": "open", "labels": "ci-regression", "per_page": "100"},
        )
    ]


def test_run_closes_existing_incident_when_failures_clear():
    module = importlib.import_module("notify_ci_regressions")
    seen = {"patches": [], "posts": []}

    class Response:
        def __init__(self, payload):
            self.payload = payload
            self.links = {}

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def get(self, url, headers=None, params=None):
            return Response(
                [
                    {
                        "number": 7550,
                        "title": "CI regression: packages now failing on GAP master",
                        "labels": [{"name": "ci-regression"}],
                    }
                ]
            )

        def post(self, url, headers=None, json=None):
            seen["posts"].append((url, json))
            return Response({"id": 1})

        def patch(self, url, headers=None, json=None):
            seen["patches"].append((url, json))
            return Response({"number": 7550, "state": "closed"})

    result = module.run_notification(
        session=Session(),
        repo="gap-system/PackageDistro",
        token="TOKEN",
        which_gap="master",
        mentions=["@user1", "@user2"],
        test_status={
            "workflow": "https://github.com/gap-system/PackageDistro/actions/runs/11",
            "id": "master/2026-04-26-01234567",
            "pkgs": {
                "atlasrep": {
                    "status": "success",
                    "version": "2.1",
                    "workflow_run": "https://example.invalid/job/atlasrep",
                }
            },
        },
        report_diff={"failure_changed": -1},
        previous_statuses={"atlasrep": "failure"},
        report_url="https://github.com/gap-system/PackageDistro/blob/data/reports/master/report.md",
    )

    assert result == {"action": "closed", "issue_number": 7550}
    assert "fully passing" in seen["posts"][0][1]["body"]
    assert seen["patches"][0][1]["state"] == "closed"
```

- [ ] **Step 2: Run the green-report tests and verify the close path fails before implementation**

Run: `python -m pytest tools/tests/test_notify_ci_regressions.py -k "no_failures or closes_existing_incident" -vv`
Expected: FAIL because the current notifier exits early or never closes an existing issue.

- [ ] **Step 3: Implement the no-failure branch that comments on and closes an open incident**

```python
def render_resolution_comment(
    which_gap: str,
    workflow_url: str,
    report_url: str,
    report_id: str,
) -> str:
    return (
        f"Latest report for GAP `{which_gap}` is now fully passing.\n\n"
        f"Report id: `{report_id}`\n\n"
        f"Workflow: {workflow_url}\n\n"
        f"Report: {report_url}\n"
    )


def run_notification(
    session: requests.Session,
    repo: str,
    token: str,
    which_gap: str,
    mentions: list[str],
    test_status: dict[str, Any],
    report_diff: dict[str, Any],
    previous_statuses: dict[str, str] | None = None,
    report_url: str | None = None,
) -> dict[str, Any]:
    current_rows = current_failures(test_status)
    changed_rows = changed_failures(test_status, previous_statuses or {})
    workflow_url = test_status["workflow"]
    issue = find_open_incident_issue(session, repo, token)
    if not current_rows:
        if issue is None:
            return {"action": "noop", "issue_number": None}
        session.post(
            f"https://api.github.com/repos/{repo}/issues/{issue['number']}/comments",
            headers=github_headers(token),
            json={
                "body": render_resolution_comment(
                    which_gap,
                    workflow_url,
                    report_url or workflow_url,
                    test_status["id"],
                )
            },
        ).raise_for_status()
        session.patch(
            f"https://api.github.com/repos/{repo}/issues/{issue['number']}",
            headers=github_headers(token),
            json={"state": "closed"},
        ).raise_for_status()
        return {"action": "closed", "issue_number": issue["number"]}
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `python -m pytest tools/tests/test_notify_ci_regressions.py -k "no_failures or closes_existing_incident" -vv`
Expected: PASS

- [ ] **Step 5: Commit the progress**

```bash
git add tools/tests/test_notify_ci_regressions.py tools/notify_ci_regressions.py
git commit -m "ci: close resolved regression issues" -m "Close the live CI regression incident after the latest GAP master report becomes fully green, and leave a resolution comment with links back to the report and workflow." -m "This prevents intermittent failures from leaving stale open incidents behind after the next clean run." -m "AI-assisted by Codex for implementation planning and code changes." -m "Co-authored-by: Codex <codex@openai.com>"
```

### Task 4: Run the full notifier test suite and project Python checks

**Files:**
- Modify: `tools/notify_ci_regressions.py`
- Modify: `tools/tests/test_notify_ci_regressions.py`
- Test: `tools/tests/test_notify_ci_regressions.py`

- [ ] **Step 1: Run the notifier test file**

Run: `python -m pytest tools/tests/test_notify_ci_regressions.py -vv`
Expected: PASS with all notifier lifecycle tests green.

- [ ] **Step 2: Run formatting and type checks relevant to Python tooling**

Run: `python -m black --check --diff tools`
Expected: PASS

Run: `python -m isort --check --profile black tools`
Expected: PASS

Run: `python -m mypy --disallow-untyped-calls --disallow-untyped-defs tools/*.py`
Expected: PASS

- [ ] **Step 3: Run the broader Python test suite because the notifier lives in shared tooling**

Run: `python -m pytest tools/tests/test*.py -vv`
Expected: PASS

- [ ] **Step 4: Review whether `CHANGELOG.md` needs an entry**

Check whether this repository has a changelog file that should be updated for the CI behavior change. If one exists and project policy expects an entry, add it in the implementation branch before the final commit.

- [ ] **Step 5: Commit any final polish**

```bash
git add tools/notify_ci_regressions.py tools/tests/test_notify_ci_regressions.py
git commit -m "ci: finalize regression issue lifecycle" -m "Run the notifier through the project Python checks and keep the workflow interface unchanged while the issue lifecycle now covers create, refresh, comment, and close behavior." -m "AI-assisted by Codex for implementation planning and code changes." -m "Co-authored-by: Codex <codex@openai.com>"
```
