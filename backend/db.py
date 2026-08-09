from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./router.db")
DB_PATH = DB_URL.replace("sqlite:///", "") if DB_URL.startswith("sqlite:///") else "./router.db"

@contextmanager
def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()

def init_db() -> None:
    with connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
              task_id TEXT PRIMARY KEY,
              candidate_id TEXT NOT NULL,
              source_email_id TEXT NOT NULL,
              thread_id TEXT NOT NULL,
              title TEXT NOT NULL,
              description TEXT,
              assignee_id TEXT NOT NULL,
              category TEXT NOT NULL,
              priority TEXT NOT NULL,
              due_date TEXT,
              deal_value_inr INTEGER,
              company_name TEXT,
              confidence REAL NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(candidate_id, source_email_id),
              UNIQUE(candidate_id, thread_id)
            );
            CREATE TABLE IF NOT EXISTS decisions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              candidate_id TEXT NOT NULL,
              run_id TEXT NOT NULL,
              email_id TEXT NOT NULL,
              thread_id TEXT NOT NULL,
              action TEXT NOT NULL,
              skip_reason TEXT,
              task_id TEXT,
              category TEXT,
              assignee_id TEXT,
              priority TEXT,
              confidence REAL,
              reasoning TEXT,
              raw_email_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(candidate_id, email_id)
            );
            CREATE TABLE IF NOT EXISTS update_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              candidate_id TEXT NOT NULL,
              thread_id TEXT NOT NULL,
              task_id TEXT NOT NULL,
              source_email_id TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
