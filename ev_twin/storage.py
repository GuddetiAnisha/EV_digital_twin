import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class PredictionStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("CREATE TABLE IF NOT EXISTS predictions (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def save(self, kind, payload):
        with self.connect() as con:
            cursor = con.execute("INSERT INTO predictions (created_at, kind, payload) VALUES (?, ?, ?)", (datetime.now(timezone.utc).isoformat(), kind, json.dumps(payload, allow_nan=False)))
            return cursor.lastrowid

    def history(self, limit=50, offset=0):
        if not 1 <= limit <= 500 or offset < 0:
            raise ValueError("limit must be 1..500 and offset non-negative")
        with self.connect() as con:
            rows = con.execute("SELECT id, created_at, kind, payload FROM predictions ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [{"id": row[0], "created_at": row[1], "kind": row[2], "payload": json.loads(row[3])} for row in rows]
