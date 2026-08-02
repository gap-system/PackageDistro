# -*- coding: utf-8 -*-
# pylint: disable=missing-function-docstring, invalid-name

"""
This module contains some tests for the generate_overview.py script
"""

import importlib
import os
import re
import sys

sys.path.insert(
    0, "/".join(os.path.dirname(os.path.realpath(__file__)).split("/")[:-1])
)

generate_overview = importlib.import_module("generate_overview")


ENTRY = {
    "name": "GAPDoc",
    "version": "1.6.10",
    "date": "2026-05-20",
    "subtitle": "A Meta Package for GAP Documentation",
    "license": "GPL-2.0-or-later",
    "maintainers": ["Frank Lübeck"],
    "home": "https://example.com/GAPDoc",
    "readme": "https://example.com/GAPDoc/README.txt",
    "archive": "https://example.com/GAPDoc-1.6.10.tar.gz",
    "source": "https://github.com/frankluebeck/GAPDoc",
    "issues": "https://github.com/frankluebeck/GAPDoc/issues",
}


def entry(**overrides):
    return {**ENTRY, **overrides}


def test_maintainers_prefers_maintainers_over_authors():
    pkg_json = {
        "Persons": [
            {"FirstNames": "Ann", "LastName": "Author", "IsAuthor": True},
            {
                "FirstNames": "Mary",
                "LastName": "Maintainer",
                "IsAuthor": True,
                "IsMaintainer": True,
            },
        ]
    }

    assert generate_overview.maintainers(pkg_json) == ["Mary Maintainer"]


def test_maintainers_falls_back_to_authors():
    pkg_json = {
        "Persons": [{"FirstNames": "Ann", "LastName": "Author", "IsAuthor": True}]
    }

    assert generate_overview.maintainers(pkg_json) == ["Ann Author"]


def test_package_entry_reads_metadata(monkeypatch):
    monkeypatch.chdir(os.path.dirname(os.path.realpath(__file__)))

    result = generate_overview.package_entry("aclib")

    assert result["name"] == "AClib"
    assert result["version"] == "1.3.2"
    assert result["archive"].endswith(".tar.gz")
    assert result["home"].startswith("http")


def test_collect_entries_sorts_case_insensitively(monkeypatch):
    monkeypatch.chdir(os.path.dirname(os.path.realpath(__file__)))

    names = [e["name"] for e in generate_overview.collect_entries(["unipot", "aclib"])]

    assert names == ["AClib", "Unipot"]


def test_row_contains_all_columns_and_links():
    row = generate_overview.render_row(entry())

    assert row.count("<td") == len(generate_overview.COLUMNS)
    for url in [ENTRY["home"], ENTRY["readme"], ENTRY["archive"], ENTRY["source"]]:
        assert f'href="{url}"' in row
    # the maintainers show up as a tooltip on the package name
    assert 'title="Frank Lübeck"' in row


def test_row_omits_links_that_are_not_known():
    row = generate_overview.render_row(entry(source="", issues=""))

    assert "code</a>" not in row
    assert "issues</a>" not in row
    assert "README</a>" in row


def test_row_escapes_metadata():
    row = generate_overview.render_row(entry(subtitle='<script>"attack"</script>'))

    assert "<script>" not in row
    assert "&lt;script&gt;" in row


def test_row_sorts_by_the_underlying_value():
    row = generate_overview.render_row(entry())

    # the name cell is rendered with markup, but sorts by the plain value
    assert '<td data-sort="GAPDoc">' in row


def test_last_metadata_change_reports_a_date(monkeypatch):
    monkeypatch.chdir(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    )

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", generate_overview.last_metadata_change())


def test_last_metadata_change_falls_back_outside_a_checkout(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(generate_overview, "today", lambda: "1970-01-01")

    assert generate_overview.last_metadata_change() == "1970-01-01"


def test_page_reports_the_number_of_packages():
    page = generate_overview.render_page([entry(), entry(name="IO")], "2026-08-02")

    assert "All 2 packages" in page
    assert ">2 packages</span>" in page
    assert "2026-08-02" in page


def test_page_is_static_html_without_front_matter():
    page = generate_overview.render_page([entry()], "2026-08-02")

    assert page.startswith("<!DOCTYPE html>")
    # Jekyll must copy the page verbatim rather than run it through Liquid
    assert "{{" not in page
    assert "{%" not in page


def test_main_writes_the_page(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(os.path.dirname(os.path.realpath(__file__)))
    monkeypatch.setattr(generate_overview, "all_packages", lambda: ["aclib", "unipot"])

    assert generate_overview.main([str(tmp_path), "--date", "2026-08-02"]) == 0

    page = (tmp_path / "packages" / "index.html").read_text(encoding="utf-8")
    assert "AClib" in page
    assert "Unipot" in page
    assert "listing 2 packages" in capsys.readouterr().out
