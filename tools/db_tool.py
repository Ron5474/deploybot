import json
import sqlite3
import sqlparse
from langchain_core.tools import tool

from db.db import DB_PATH

@tool
def query_app_db(sql_query):
    """
    Use this to query the self-hosted apps database. Input should be a valid SELECT SQL query against apps table which has columns: 
    name, category, description, github_url, license, language.
    """
    parsed_sql = sqlparse.parse(sql_query)

    if len(parsed_sql) != 1 or parsed_sql[0].get_type() != "SELECT":
        return "Invalid SQL Query"

    # The SQL is written by the LLM, so open the database read-only: even a
    # statement that slips past the SELECT check above cannot change data.
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    except sqlite3.Error as e:
        return f"Query error: {str(e)}"
    cursor = conn.cursor()

    try:
        cursor.execute(sql_query)
    except Exception as e:
        conn.close()
        return f"Query error: {str(e)}"

    rows = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description]
    # Return a list of dicts for easier parsing by LLM
    results = [dict(zip(cols, row)) for row in rows]

    conn.close()
    return json.dumps(results, indent=2) 





