import json
import sqlite3

import pytest

from tools import db_tool
from tools.db_tool import query_app_db


@pytest.fixture
def apps_db(tmp_path, monkeypatch):
    """A throwaway apps database; the tool is pointed at it instead of apps.db."""
    path = tmp_path / "apps.db"
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE apps (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            category TEXT,
            description TEXT,
            github_url TEXT,
            docker_image TEXT,
            license TEXT,
            language TEXT
        )
        """
    )
    conn.executemany(
        "INSERT INTO apps (name, category, license, language) VALUES (?, ?, ?, ?)",
        [
            ("Nextcloud", "File Sync", "AGPL-3.0", "PHP"),
            ("Jellyfin", "Media Streaming", "GPL-2.0", "C#"),
            ("Gitea", "Software Development", "MIT", "Go"),
        ],
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(db_tool, "DB_PATH", path)
    return path


def run(sql):
    return query_app_db.invoke({"sql_query": sql})


def app_names(path):
    conn = sqlite3.connect(path)
    names = [row[0] for row in conn.execute("SELECT name FROM apps ORDER BY name")]
    conn.close()
    return names


def test_select_returns_rows_as_json(apps_db):
    result = run("SELECT name, license FROM apps WHERE language = 'Go'")
    assert json.loads(result) == [{"name": "Gitea", "license": "MIT"}]


def test_select_with_no_matches_returns_empty_list(apps_db):
    assert json.loads(run("SELECT name FROM apps WHERE language = 'COBOL'")) == []


@pytest.mark.parametrize("sql", [
    "DROP TABLE apps",
    "DELETE FROM apps",
    "INSERT INTO apps (name) VALUES ('evil')",
    "UPDATE apps SET name = 'evil'",
    "WITH t AS (SELECT 1) DELETE FROM apps",
    "PRAGMA table_info(apps)",
])
def test_rejects_non_select_statements(apps_db, sql):
    assert run(sql) == "Invalid SQL Query"
    assert app_names(apps_db) == ["Gitea", "Jellyfin", "Nextcloud"]


@pytest.mark.parametrize("sql", [
    "SELECT 1; DROP TABLE apps",
    "SELECT name FROM apps; DELETE FROM apps",
])
def test_rejects_multiple_statements(apps_db, sql):
    assert run(sql) == "Invalid SQL Query"
    assert app_names(apps_db) == ["Gitea", "Jellyfin", "Nextcloud"]


def test_invalid_select_reports_query_error(apps_db):
    assert run("SELECT nope FROM apps").startswith("Query error:")


def test_write_is_refused_even_if_the_select_check_is_bypassed(apps_db, monkeypatch):
    # Simulate a statement slipping past the first layer: make the parser call
    # every statement a SELECT, then check the connection itself refuses to write.
    class LooksLikeSelect:
        def get_type(self):
            return "SELECT"

    monkeypatch.setattr(db_tool.sqlparse, "parse", lambda sql: [LooksLikeSelect()])

    result = run("DELETE FROM apps")

    assert result.startswith("Query error:")
    assert "readonly" in result
    assert app_names(apps_db) == ["Gitea", "Jellyfin", "Nextcloud"]


def test_missing_database_reports_error_instead_of_creating_one(tmp_path, monkeypatch):
    missing = tmp_path / "missing.db"
    monkeypatch.setattr(db_tool, "DB_PATH", missing)

    assert run("SELECT name FROM apps").startswith("Query error:")
    assert not missing.exists()
