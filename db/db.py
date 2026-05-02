import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "apps.db"


def setup_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = """
        CREATE TABLE IF NOT EXISTS apps (
            id              INTEGER PRIMARY KEY,
            name            TEXT NOT NULL UNIQUE,
            category        TEXT,
            description     TEXT,
            github_url      TEXT,
            docker_image    TEXT,
            license         TEXT,
            language        TEXT

        );
    """
    cursor.execute(query)
    conn.commit()

    return conn, cursor

