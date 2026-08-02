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
Generate an overview page listing all packages in the distribution.

The result is a single self-contained HTML file: it carries its own style
sheet and the bit of JavaScript that makes the table searchable and sortable,
so that it can simply be dropped into the `gh-pages` worktree and served from
https://gap-system.github.io/PackageDistro/packages/ without any build step.

Deliberately no YAML front matter is emitted: Jekyll copies such files
verbatim, which keeps the page independent of the site theme and stops Liquid
from touching the embedded script.
"""

import argparse
import datetime
import html
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

from utils import all_packages, archive_url, metadata

# Path of the generated page, relative to the output directory. The page lives
# in a directory of its own so that it is served under a clean `.../packages/`
# URL.
PAGE_PATH = os.path.join("packages", "index.html")

REPO_URL = "https://github.com/gap-system/PackageDistro"

# Columns of the table, in order. `key` is the field of the entries produced by
# `package_entry`, `sortable` marks the columns whose header toggles sorting.
COLUMNS = [
    ("name", "Package", True),
    ("version", "Version", True),
    ("date", "Released", True),
    ("subtitle", "Description", False),
    ("license", "License", True),
    ("links", "Links", False),
]


def person_name(person: Dict[str, Any]) -> str:
    return " ".join(
        part for part in [person.get("FirstNames"), person.get("LastName")] if part
    )


def maintainers(pkg_json: Dict[str, Any]) -> List[str]:
    """The names of the maintainers of a package.

    Some packages have no maintainer flagged at all; for those we fall back to
    the authors, as an overview listing nobody is less useful than one listing
    the people who wrote the package.
    """
    persons = pkg_json.get("Persons", [])
    names = [person_name(p) for p in persons if p.get("IsMaintainer")]
    if not names:
        names = [person_name(p) for p in persons if p.get("IsAuthor")]
    return [name for name in names if name]


def package_entry(pkg_name: str) -> Dict[str, Any]:
    """Collect everything the overview page shows about a single package."""
    pkg_json = metadata(pkg_name)
    source = pkg_json.get("SourceRepository") or {}
    return {
        "name": pkg_json["PackageName"],
        "version": pkg_json["Version"],
        "date": pkg_json["Date"],
        "subtitle": pkg_json["Subtitle"],
        "license": pkg_json["License"],
        "maintainers": maintainers(pkg_json),
        "home": pkg_json["PackageWWWHome"],
        "readme": pkg_json["README_URL"],
        "archive": archive_url(pkg_json),
        "source": source.get("URL") or "",
        "issues": pkg_json.get("IssueTrackerURL") or "",
    }


def collect_entries(pkg_names: List[str]) -> List[Dict[str, Any]]:
    entries = [package_entry(pkg_name) for pkg_name in pkg_names]
    return sorted(entries, key=lambda entry: entry["name"].lower())


def link(url: str, text: str) -> str:
    return f'<a href="{html.escape(url)}">{html.escape(text)}</a>'


def cell(entry: Dict[str, Any], key: str) -> str:
    """Render the table cell of column `key` for one package."""
    if key == "name":
        # The name links to the package home page, the tooltip names the people
        # to talk to about the package.
        title = ", ".join(entry["maintainers"])
        attr = f' title="{html.escape(title)}"' if title else ""
        return f'<span{attr}>{link(entry["home"], entry["name"])}</span>'
    if key == "links":
        links = [
            ("README", entry["readme"]),
            ("archive", entry["archive"]),
            ("code", entry["source"]),
            ("issues", entry["issues"]),
        ]
        return " · ".join(link(url, text) for text, url in links if url)
    return html.escape(str(entry[key]))


def render_row(entry: Dict[str, Any]) -> str:
    cells = []
    for key, _, _ in COLUMNS:
        # `data-sort` gives the sorting code the plain value, so that the links
        # and tooltips a cell may contain cannot influence the order.
        attrs = f' data-sort="{html.escape(str(entry[key]))}"' if key in entry else ""
        cells.append(f"<td{attrs}>{cell(entry, key)}</td>")
    return "    <tr>" + "".join(cells) + "</tr>"


def render_head() -> str:
    headers = []
    for index, (_, title, sortable) in enumerate(COLUMNS):
        if sortable:
            headers.append(
                f'<th class="sortable" data-column="{index}"'
                f' tabindex="0" role="button">{html.escape(title)}</th>'
            )
        else:
            headers.append(f"<th>{html.escape(title)}</th>")
    return "    <tr>" + "".join(headers) + "</tr>"


STYLE = """
:root {
  color-scheme: light dark;
  --fg: #1a1a1a;
  --bg: #ffffff;
  --muted: #5a5a5a;
  --border: #d8d8d8;
  --stripe: #f6f6f6;
  --accent: #1c5aa8;
}
@media (prefers-color-scheme: dark) {
  :root {
    --fg: #e8e8e8;
    --bg: #14171a;
    --muted: #a0a6ac;
    --border: #333a41;
    --stripe: #1b1f23;
    --accent: #79b8ff;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0 auto;
  padding: 1.5rem 1rem 4rem;
  max-width: 78rem;
  color: var(--fg);
  background: var(--bg);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial,
    sans-serif;
  line-height: 1.5;
}
a { color: var(--accent); }
h1 { margin-bottom: 0.25rem; font-size: 1.75rem; }
p.intro { margin-top: 0; color: var(--muted); }
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: baseline;
  margin: 1.25rem 0 0.75rem;
}
#filter {
  flex: 1 1 18rem;
  padding: 0.5rem 0.65rem;
  color: inherit;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 0.35rem;
  font: inherit;
}
#count { color: var(--muted); font-size: 0.9rem; }
.table-wrapper { overflow-x: auto; }
/* The minimum width keeps the columns readable on narrow screens; the wrapper
   turns the overflow into horizontal scrolling of the table alone. */
table {
  width: 100%;
  min-width: 58rem;
  border-collapse: collapse;
  font-size: 0.92rem;
}
th, td {
  padding: 0.45rem 0.6rem;
  text-align: left;
  vertical-align: top;
  border-bottom: 1px solid var(--border);
}
thead th {
  position: sticky;
  top: 0;
  background: var(--bg);
  border-bottom: 2px solid var(--border);
  white-space: nowrap;
}
th.sortable { cursor: pointer; }
th.sortable::after { content: " \\2195"; color: var(--muted); }
th.sortable[aria-sort="ascending"]::after { content: " \\2191"; color: var(--fg); }
th.sortable[aria-sort="descending"]::after { content: " \\2193"; color: var(--fg); }
tbody tr:nth-child(even of :not([hidden])) { background: var(--stripe); }
td:nth-child(1), td:nth-child(2), td:nth-child(3) { white-space: nowrap; }
td:last-child { white-space: nowrap; font-size: 0.85rem; }
footer { margin-top: 2rem; color: var(--muted); font-size: 0.85rem; }
"""

SCRIPT = """
(function () {
  var table = document.getElementById("packages");
  var tbody = table.tBodies[0];
  var rows = Array.prototype.slice.call(tbody.rows);
  var filter = document.getElementById("filter");
  var count = document.getElementById("count");
  var collator = new Intl.Collator(undefined, {numeric: true, sensitivity: "base"});
  var sortColumn = -1;
  var ascending = true;

  function sortKey(row, column) {
    var cell = row.cells[column];
    return cell.dataset.sort !== undefined ? cell.dataset.sort : cell.textContent;
  }

  function sort(column) {
    if (column === sortColumn) {
      ascending = !ascending;
    } else {
      sortColumn = column;
      ascending = true;
    }
    var sorted = rows.slice().sort(function (a, b) {
      var result = collator.compare(sortKey(a, column), sortKey(b, column));
      return ascending ? result : -result;
    });
    sorted.forEach(function (row) { tbody.appendChild(row); });
    Array.prototype.forEach.call(table.tHead.rows[0].cells, function (th) {
      if (Number(th.dataset.column) === column) {
        th.setAttribute("aria-sort", ascending ? "ascending" : "descending");
      } else {
        th.removeAttribute("aria-sort");
      }
    });
  }

  function apply() {
    var needle = filter.value.trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (row) {
      var match = needle === "" || row.textContent.toLowerCase().indexOf(needle) !== -1;
      row.hidden = !match;
      if (match) { shown += 1; }
    });
    count.textContent = shown === rows.length
      ? rows.length + " packages"
      : shown + " of " + rows.length + " packages";
  }

  Array.prototype.forEach.call(table.tHead.rows[0].cells, function (th) {
    if (!th.classList.contains("sortable")) { return; }
    var column = Number(th.dataset.column);
    th.addEventListener("click", function () { sort(column); });
    th.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        sort(column);
      }
    });
  });

  filter.addEventListener("input", apply);
  apply();
})();
"""


def render_page(entries: List[Dict[str, Any]], generated: str) -> str:
    """Render the overview page for `entries`, stamped with the date `generated`."""
    rows = "\n".join(render_row(entry) for entry in entries)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GAP package distribution</title>
<style>{STYLE}</style>
</head>
<body>
<h1>GAP package distribution</h1>
<p class="intro">
All {len(entries)} packages in the GAP package distribution. The versions listed
here are the ones redistributed with GAP; follow a package name for its home
page. Generated from
<a href="{REPO_URL}">gap-system/PackageDistro</a>, last updated
{html.escape(generated)}.
</p>
<div class="controls">
<input id="filter" type="search" aria-label="Filter packages"
 placeholder="Filter by name, description, license, ..." autocomplete="off" autofocus>
<span id="count">{len(entries)} packages</span>
</div>
<div class="table-wrapper">
<table id="packages">
  <thead>
{render_head()}
  </thead>
  <tbody>
{rows}
  </tbody>
</table>
</div>
<footer>
<a href="../">Package distribution status page</a> ·
<a href="{REPO_URL}">Repository</a> ·
<a href="{REPO_URL}/issues">Report a problem with this page</a>
</footer>
<script>{SCRIPT}</script>
</body>
</html>
"""


def last_metadata_change() -> str:
    """The date of the last commit touching the package metadata.

    The page is dated by the data it shows rather than by the moment it was
    generated: that is both the more useful date for a reader, and it keeps
    regenerating an unchanged distribution from producing a new page -- and
    hence a pointless commit on the `gh-pages` branch -- every day.

    Outside a git checkout we fall back to today.
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", "packages"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return today()
    return result.stdout.strip() or today()


def today() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def write_page(outdir: str, page: str) -> str:
    path = os.path.join(outdir, PAGE_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "outdir",
        nargs="?",
        default="gh-pages",
        help="directory to write the page into (default: %(default)s)",
    )
    parser.add_argument(
        "--date",
        help="date to stamp the page with "
        "(default: the date of the last change to the package metadata)",
    )
    args = parser.parse_args(argv)
    date = args.date or last_metadata_change()

    entries = collect_entries(all_packages())
    path = write_page(args.outdir, render_page(entries, date))
    print(f"wrote {path} listing {len(entries)} packages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
