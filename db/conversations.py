import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "conversation_history.db"

def _ensure_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            is_deleted INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        conn.execute("ALTER TABLE chat_history ADD COLUMN is_deleted INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE chat_history ADD COLUMN client_id TEXT DEFAULT ''")
    except Exception:
        pass

    conn.commit()
    conn.close()

_ensure_table()

def get_history(session_id: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY timestamp",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]

def save_message(session_id: str, role: str, content: str, client_id: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (session_id, role, content, client_id) VALUES (?, ?, ?, ?)",
        (session_id, role, content, client_id)
    )
    conn.commit()
    conn.close()

def get_all_sessions(client_id: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_id, content, timestamp
        FROM chat_history
        WHERE role = 'human'
        AND is_deleted = 0
        AND client_id = ?
        AND id IN (
                SELECT MIN(id) FROM chat_history
                WHERE role = 'human'
                AND client_id = ?
                GROUP BY session_id
            )
        ORDER BY timestamp DESC
    """, (client_id, client_id))
    rows = cursor.fetchall()
    conn.close()
    return [{"session_id": row[0], "preview": row[1][:60], "timestamp": row[2]} for row in rows]


def get_session_messages(session_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM chat_history WHERE session_id = ? AND is_deleted = 0 ORDER BY timestamp",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]


def delete_last_exchange(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM chat_history
        WHERE id IN (
            SELECT id FROM chat_history
            WHERE session_id = ? AND is_deleted = 0
            ORDER BY id DESC
            LIMIT 2
        )
    """, (session_id,))
    conn.commit()
    conn.close()

def delete_session(session_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE chat_history SET is_deleted = 1 WHERE session_id = ?",
        (session_id,)
    )
    conn.commit()
    conn.close()

