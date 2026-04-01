import sqlite3
import pandas as pd
from datetime import date

DB_PATH = "timetracker.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT NOT NULL DEFAULT '#4A90E2',
            default_rate REAL NOT NULL DEFAULT 0.0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            hours REAL NOT NULL,
            rate REAL NOT NULL,
            total REAL GENERATED ALWAYS AS (hours * rate) STORED,
            note TEXT DEFAULT '',
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

# ── Clients ──────────────────────────────────────────────────────────────────

def add_client(name: str, color: str, default_rate: float):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO clients (name, color, default_rate) VALUES (?, ?, ?)",
            (name, color, default_rate)
        )
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, "Un client avec ce nom existe déjà."
    finally:
        conn.close()

def get_clients() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM clients ORDER BY name", conn)
    conn.close()
    return df

def update_client(client_id: int, name: str, color: str, default_rate: float):
    conn = get_conn()
    conn.execute(
        "UPDATE clients SET name=?, color=?, default_rate=? WHERE id=?",
        (name, color, default_rate, client_id)
    )
    conn.commit()
    conn.close()

def delete_client(client_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()
    conn.close()

# ── Sessions ──────────────────────────────────────────────────────────────────

def add_session(client_id: int, work_date: date, hours: float, rate: float, note: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO sessions (client_id, work_date, hours, rate, note) VALUES (?, ?, ?, ?, ?)",
        (client_id, work_date.isoformat(), hours, rate, note)
    )
    conn.commit()
    conn.close()

def get_sessions_full() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("""
        SELECT s.id, c.name AS client, c.color, s.work_date, s.hours, s.rate, s.total, s.note
        FROM sessions s
        JOIN clients c ON s.client_id = c.id
        ORDER BY s.work_date DESC
    """, conn)
    conn.close()
    if not df.empty:
        df["work_date"] = pd.to_datetime(df["work_date"])
    return df

def delete_session(session_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
    conn.commit()
    conn.close()

def get_monthly_summary() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("""
        SELECT
            strftime('%Y-%m', work_date) AS mois,
            c.name AS client,
            c.color,
            SUM(hours) AS total_heures,
            SUM(total) AS total_euros
        FROM sessions s
        JOIN clients c ON s.client_id = c.id
        GROUP BY mois, client
        ORDER BY mois DESC, client
    """, conn)
    conn.close()
    return df
