import streamlit as st
import pandas as pd
from datetime import date, timedelta
from supabase import create_client, Client

# ── Connexion Supabase ────────────────────────────────────────────────────────

@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def init_db():
    pass

# ── Settings ──────────────────────────────────────────────────────────────────

def get_settings() -> dict:
    sb = get_client()
    try:
        resp = sb.table("settings").select("*").execute()
        if resp.data:
            s = resp.data[0]
            return {
                "app_name":  s.get("app_name", "Time Tracker"),
                "currency":  s.get("currency", "€"),
                "dark_mode": s.get("dark_mode", False),
            }
    except Exception:
        pass
    return {"app_name": "Time Tracker", "currency": "€", "dark_mode": False}

def save_settings(app_name: str, currency: str, dark_mode: bool):
    sb = get_client()
    try:
        resp = sb.table("settings").select("id").execute()
        data = {"app_name": app_name, "currency": currency, "dark_mode": dark_mode}
        if resp.data:
            sb.table("settings").update(data).eq("id", resp.data[0]["id"]).execute()
        else:
            sb.table("settings").insert(data).execute()
    except Exception:
        pass

# ── Clients ───────────────────────────────────────────────────────────────────

def add_client(name: str, color: str, default_rate: float, tva: float = 0.0):
    sb = get_client()
    try:
        sb.table("clients").insert({
            "name": name, "color": color,
            "default_rate": default_rate, "tva": tva
        }).execute()
        return True, None
    except Exception as e:
        msg = str(e)
        if "unique" in msg.lower() or "duplicate" in msg.lower():
            return False, "Un client avec ce nom existe déjà."
        return False, msg

def get_clients() -> pd.DataFrame:
    sb = get_client()
    resp = sb.table("clients").select("*").order("name").execute()
    if resp.data:
        df = pd.DataFrame(resp.data)
        if "tva" not in df.columns:
            df["tva"] = 0.0
        return df
    return pd.DataFrame(columns=["id", "name", "color", "default_rate", "tva"])

def update_client(client_id: int, name: str, color: str, default_rate: float, tva: float = 0.0):
    sb = get_client()
    sb.table("clients").update({
        "name": name, "color": color,
        "default_rate": default_rate, "tva": tva
    }).eq("id", client_id).execute()

def delete_client(client_id: int):
    sb = get_client()
    sb.table("clients").delete().eq("id", client_id).execute()

# ── Sessions ──────────────────────────────────────────────────────────────────

def add_session(client_id: int, work_date: date, hours: float, rate: float, note: str):
    sb = get_client()
    sb.table("sessions").insert({
        "client_id": client_id,
        "work_date": work_date.isoformat(),
        "hours": hours, "rate": rate, "note": note
    }).execute()

def update_session(session_id: int, client_id: int, work_date: date,
                   hours: float, rate: float, note: str):
    sb = get_client()
    sb.table("sessions").update({
        "client_id": client_id,
        "work_date": work_date.isoformat(),
        "hours": hours, "rate": rate, "note": note
    }).eq("id", session_id).execute()

def duplicate_session(session_id: int, new_date: date):
    sb = get_client()
    resp = sb.table("sessions").select("*").eq("id", session_id).execute()
    if resp.data:
        s = resp.data[0]
        sb.table("sessions").insert({
            "client_id": s["client_id"],
            "work_date": new_date.isoformat(),
            "hours": s["hours"], "rate": s["rate"], "note": s["note"]
        }).execute()

def add_recurring_sessions(client_id: int, hours: float, rate: float, note: str,
                            weekday: int, start_date: date, end_date: date):
    sb = get_client()
    current = start_date
    records = []
    while current <= end_date:
        if current.weekday() == weekday:
            records.append({
                "client_id": client_id,
                "work_date": current.isoformat(),
                "hours": hours, "rate": rate, "note": note
            })
        current += timedelta(days=1)
    if records:
        sb.table("sessions").insert(records).execute()
    return len(records)

def get_sessions_full() -> pd.DataFrame:
    sb = get_client()
    resp = sb.table("sessions").select(
        "id, work_date, hours, rate, total, note, client_id, clients(name, color, tva)"
    ).order("work_date", desc=True).execute()

    if not resp.data:
        return pd.DataFrame(columns=["id", "client_id", "client", "color", "tva",
                                     "work_date", "hours", "rate", "total", "note"])
    rows = []
    for r in resp.data:
        rows.append({
            "id":        r["id"],
            "client_id": r["client_id"],
            "client":    r["clients"]["name"],
            "color":     r["clients"]["color"],
            "tva":       r["clients"].get("tva", 0.0) or 0.0,
            "work_date": r["work_date"],
            "hours":     r["hours"],
            "rate":      r["rate"],
            "total":     r["total"],
            "note":      r["note"] or ""
        })
    df = pd.DataFrame(rows)
    df["work_date"] = pd.to_datetime(df["work_date"])
    return df

def delete_session(session_id: int):
    sb = get_client()
    sb.table("sessions").delete().eq("id", session_id).execute()

def get_monthly_summary() -> pd.DataFrame:
    df = get_sessions_full()
    if df.empty:
        return pd.DataFrame(columns=["mois", "client", "color", "total_heures", "total_euros"])
    df["mois"] = df["work_date"].dt.strftime("%Y-%m")
    return df.groupby(["mois", "client", "color"], as_index=False).agg(
        total_heures=("hours", "sum"),
        total_euros=("total", "sum")
    ).sort_values(["mois", "client"], ascending=[False, True])
