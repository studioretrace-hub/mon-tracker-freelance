import streamlit as st
import pandas as pd
import calendar
from datetime import date, timedelta
from database import (
    init_db, get_settings, save_settings,
    add_client, get_clients, update_client, delete_client,
    add_session, update_session, duplicate_session, add_recurring_sessions,
    get_sessions_full, delete_session, get_monthly_summary
)

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()
cfg = get_settings()
APP_NAME = cfg.get("app_name", "Time Tracker")
CURRENCY = cfg.get("currency", "€")
DARK     = cfg.get("dark_mode", False)

st.set_page_config(page_title=APP_NAME, page_icon="🗓️", layout="wide")

# ── Theme CSS ─────────────────────────────────────────────────────────────────
if DARK:
    BG, CARD, TEXT, BORDER, SUBTEXT = "#0e1117", "#1e2130", "#fafafa", "#2e3250", "#aab"
else:
    BG, CARD, TEXT, BORDER, SUBTEXT = "#f5f7fb", "#ffffff", "#1a1a2e", "#e0e4ef", "#888"

st.markdown(f"""
<style>
    .appview-container .main .block-container {{ padding-top: 1.5rem; }}
    section[data-testid="stSidebar"] {{ background: {CARD}; }}
    div[data-testid="stMetric"] {{
        background: {CARD};
        border-radius: 12px;
        padding: 14px 18px;
        border-left: 4px solid #4A90E2;
        box-shadow: 0 1px 4px rgba(0,0,0,.06);
    }}
    .cal-header {{
        text-align:center; font-weight:700;
        color:{SUBTEXT}; font-size:.75rem; padding:4px 0 6px;
        text-transform:uppercase; letter-spacing:.05em;
    }}
    .cal-cell {{
        border:1px solid {BORDER}; background:{CARD};
        border-radius:10px; padding:6px 4px;
        text-align:center; min-height:72px;
        transition: box-shadow .15s;
    }}
    .cal-cell-today {{ border:2.5px solid #4A90E2 !important; }}
    .cal-cell-work  {{ background:#eef4ff; }}
    .dot {{
        display:inline-block; width:9px; height:9px;
        border-radius:3px; margin:1px;
    }}
    .tag {{
        display:inline-block; border-radius:5px;
        padding:2px 9px; color:white; font-size:.78rem; font-weight:600;
    }}
    h1,h2,h3 {{ color:{TEXT}; }}
    .stDataFrame {{ border-radius:12px; overflow:hidden; }}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"## 🗓️ {APP_NAME}")
    page = st.radio("Nav", [
        "🏠 Dashboard", "📅 Calendrier", "➕ Saisir une session",
        "🔁 Sessions récurrentes", "👥 Clients", "📊 Récapitulatif",
        "📤 Export", "⚙️ Paramètres"
    ], label_visibility="collapsed")
    st.divider()
    clients_df = get_clients()
    if not clients_df.empty:
        st.markdown("**Clients**")
        for _, row in clients_df.iterrows():
            st.markdown(
                f"<span class='tag' style='background:{row.color}'>● {row['name']}</span>&nbsp;",
                unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_money(v): return f"{v:,.2f} {CURRENCY}"
def fmt_hours(v): return f"{v:.1f}h"

MONTH_FR = ["Janvier","Février","Mars","Avril","Mai","Juin",
            "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
DAY_FR   = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]
WEEKDAY_FR = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.title(f"🏠 Bonjour — {APP_NAME}")
    sessions_df = get_sessions_full()
    today = date.today()

    if sessions_df.empty:
        st.info("Aucune session. Commence par ajouter un client puis saisir des sessions !")
    else:
        # KPIs mois en cours
        cur_mask = (sessions_df["work_date"].dt.month == today.month) & \
                   (sessions_df["work_date"].dt.year  == today.year)
        cur = sessions_df[cur_mask]
        prev_month = (today.replace(day=1) - timedelta(days=1))
        prev_mask = (sessions_df["work_date"].dt.month == prev_month.month) & \
                    (sessions_df["work_date"].dt.year  == prev_month.year)
        prev = sessions_df[prev_mask]

        def delta(cur_val, prev_val):
            if prev_val == 0: return None
            return f"{((cur_val - prev_val)/prev_val*100):+.0f}% vs mois préc."

        h_cur  = cur["hours"].sum()
        e_cur  = cur["total"].sum()
        h_prev = prev["hours"].sum()
        e_prev = prev["total"].sum()

        st.markdown(f"### 📆 {MONTH_FR[today.month-1]} {today.year}")
        k1,k2,k3,k4 = st.columns(4)
        k1.metric("⏱ Heures", fmt_hours(h_cur),  delta(h_cur, h_prev))
        k2.metric(f"💶 Revenus HT", fmt_money(e_cur), delta(e_cur, e_prev))
        k3.metric("📋 Sessions", len(cur))
        k4.metric("👥 Clients actifs", cur["client"].nunique())

        st.divider()

        # Graphique barres revenus 6 derniers mois
        st.subheader("📈 Revenus des 6 derniers mois")
        sessions_df["mois"] = sessions_df["work_date"].dt.to_period("M")
        last6 = sorted(sessions_df["mois"].unique())[-6:]
        bar_data = sessions_df[sessions_df["mois"].isin(last6)].groupby("mois")["total"].sum().reset_index()
        bar_data["mois_label"] = bar_data["mois"].astype(str)
        st.bar_chart(bar_data.set_index("mois_label")["total"])

        st.divider()

        # Camembert répartition par client (mois en cours)
        st.subheader(f"🥧 Répartition par client — {MONTH_FR[today.month-1]}")
        if not cur.empty:
            pie_data = cur.groupby(["client","color"])["total"].sum().reset_index()
            total_pie = pie_data["total"].sum()
            cols = st.columns(len(pie_data))
            for i, (_, row) in enumerate(pie_data.iterrows()):
                pct = row["total"] / total_pie * 100
                cols[i].markdown(
                    f"<div style='text-align:center'>"
                    f"<span class='tag' style='background:{row.color}'>{row['client']}</span><br>"
                    f"<b>{fmt_money(row['total'])}</b><br>"
                    f"<span style='color:{SUBTEXT};font-size:.85rem'>{pct:.0f}%</span></div>",
                    unsafe_allow_html=True)
        else:
            st.info("Pas de sessions ce mois-ci.")

        # Tableau annuel
        st.divider()
        st.subheader(f"📅 Bilan {today.year}")
        summary_df = get_monthly_summary()
        if not summary_df.empty:
            annual = summary_df[summary_df["mois"].str.startswith(str(today.year))]
            if not annual.empty:
                pivot_h = annual.pivot_table(index="client", columns="mois",
                                             values="total_heures", aggfunc="sum", fill_value=0)
                pivot_e = annual.pivot_table(index="client", columns="mois",
                                             values="total_euros", aggfunc="sum", fill_value=0)
                pivot_h.columns = [MONTH_FR[int(c[-2:])-1][:3] for c in pivot_h.columns]
                pivot_e.columns = [MONTH_FR[int(c[-2:])-1][:3] for c in pivot_e.columns]
                tab1, tab2 = st.tabs(["Heures", "Revenus"])
                with tab1: st.dataframe(pivot_h.style.format("{:.1f}h"), use_container_width=True)
                with tab2: st.dataframe(pivot_e.style.format(f"{{:.0f}}{CURRENCY}"), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : CALENDRIER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📅 Calendrier":
    st.title("📅 Calendrier")
    sessions_df = get_sessions_full()
    today = date.today()

    # Navigation mois
    if "cal_month" not in st.session_state: st.session_state.cal_month = today.month
    if "cal_year"  not in st.session_state: st.session_state.cal_year  = today.year

    nav1, nav2, nav3 = st.columns([1, 3, 1])
    with nav1:
        if st.button("◀ Mois préc."):
            if st.session_state.cal_month == 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
            else:
                st.session_state.cal_month -= 1
            st.rerun()
    with nav2:
        st.markdown(
            f"<h3 style='text-align:center;margin:0'>"
            f"{MONTH_FR[st.session_state.cal_month-1]} {st.session_state.cal_year}</h3>",
            unsafe_allow_html=True)
    with nav3:
        if st.button("Mois suiv. ▶"):
            if st.session_state.cal_month == 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
            else:
                st.session_state.cal_month += 1
            st.rerun()

    sel_month = st.session_state.cal_month
    sel_year  = st.session_state.cal_year

    # Filtrer sessions du mois
    if not sessions_df.empty:
        mask = (sessions_df["work_date"].dt.month == sel_month) & \
               (sessions_df["work_date"].dt.year  == sel_year)
        month_sessions = sessions_df[mask].copy()
    else:
        month_sessions = pd.DataFrame()

    # Calendrier
    cal = calendar.monthcalendar(sel_year, sel_month)
    header_cols = st.columns(7)
    for i, dn in enumerate(DAY_FR):
        header_cols[i].markdown(f"<div class='cal-header'>{dn}</div>", unsafe_allow_html=True)

    # Saisie rapide : état
    if "quick_date" not in st.session_state: st.session_state.quick_date = None

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown("<div style='min-height:72px'></div>", unsafe_allow_html=True)
                    continue
                day_date = date(sel_year, sel_month, day)
                is_today = day_date == today
                today_cls = "cal-cell-today" if is_today else ""

                if not month_sessions.empty:
                    ds = month_sessions[month_sessions["work_date"].dt.date == day_date]
                else:
                    ds = pd.DataFrame()

                work_cls = "cal-cell-work" if not ds.empty else ""
                dots, total_day = "", ""
                if not ds.empty:
                    th = ds["hours"].sum(); te = ds["total"].sum()
                    total_day = f"<div style='font-size:.68rem;color:#4A90E2;font-weight:700'>{th:.1f}h · {te:.0f}{CURRENCY}</div>"
                    for _, s in ds.iterrows():
                        dots += f"<span class='dot' style='background:{s.color}'></span>"

                day_weight = "font-weight:700" if is_today else ""
                st.markdown(f"""
                <div class='cal-cell {today_cls} {work_cls}'>
                    <div style='font-size:.9rem;{day_weight}'>{day}</div>
                    <div>{dots}</div>{total_day}
                </div>""", unsafe_allow_html=True)

                # Bouton saisie rapide
                if st.button("＋", key=f"q_{day_date}", help=f"Saisir le {day_date.strftime('%d/%m')}"):
                    st.session_state.quick_date = day_date
                    st.rerun()

    # Modal saisie rapide
    if st.session_state.quick_date:
        qd = st.session_state.quick_date
        st.divider()
        st.subheader(f"⚡ Saisie rapide — {qd.strftime('%-d %B %Y')}")
        clients_df = get_clients()
        if clients_df.empty:
            st.warning("Crée d'abord un client dans 👥 Clients.")
            st.session_state.quick_date = None
        else:
            with st.form("quick_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                qclient = c1.selectbox("Client", clients_df["name"].tolist())
                qrow = clients_df[clients_df["name"] == qclient].iloc[0]
                qhours = c2.number_input("Heures", 0.25, 24.0, 1.0, 0.25)
                qrate  = c3.number_input("Taux (€/h)", 0.0, value=float(qrow["default_rate"]), step=5.0)
                qnote  = st.text_input("Note")
                col_ok, col_cancel = st.columns(2)
                if col_ok.form_submit_button("✅ Enregistrer", use_container_width=True):
                    add_session(int(qrow["id"]), qd, qhours, qrate, qnote)
                    st.session_state.quick_date = None
                    st.success("Session ajoutée !")
                    st.rerun()
                if col_cancel.form_submit_button("Annuler", use_container_width=True):
                    st.session_state.quick_date = None
                    st.rerun()

    # Liste sessions du mois + édition/duplique
    if not month_sessions.empty:
        st.divider()
        st.markdown("**Sessions du mois**")
        clients_df = get_clients()

        for _, row in month_sessions.iterrows():
            exp_label = f"{row['work_date'].strftime('%-d %B')} · {row['client']} · {row['hours']}h · {row['total']:.0f}{CURRENCY}"
            with st.expander(exp_label):
                tab_edit, tab_dup = st.tabs(["✏️ Modifier", "📋 Dupliquer"])

                with tab_edit:
                    with st.form(f"edit_sess_{row['id']}"):
                        c1, c2 = st.columns(2)
                        client_names = clients_df["name"].tolist()
                        cur_idx = client_names.index(row["client"]) if row["client"] in client_names else 0
                        ec = c1.selectbox("Client", client_names, index=cur_idx)
                        ed = c2.date_input("Date", value=row["work_date"].date())
                        c3, c4 = st.columns(2)
                        eh = c3.number_input("Heures", 0.25, 24.0, float(row["hours"]), 0.25)
                        er = c4.number_input("Taux", 0.0, value=float(row["rate"]), step=5.0)
                        en = st.text_input("Note", value=row["note"])
                        ca, cb = st.columns(2)
                        if ca.form_submit_button("💾 Enregistrer", use_container_width=True):
                            cid = int(clients_df[clients_df["name"]==ec].iloc[0]["id"])
                            update_session(int(row["id"]), cid, ed, eh, er, en)
                            st.success("Modifié !")
                            st.rerun()
                        if cb.form_submit_button("🗑️ Supprimer", use_container_width=True):
                            delete_session(int(row["id"]))
                            st.rerun()

                with tab_dup:
                    with st.form(f"dup_sess_{row['id']}"):
                        new_d = st.date_input("Nouvelle date", value=row["work_date"].date() + timedelta(days=1))
                        if st.form_submit_button("📋 Dupliquer sur cette date", use_container_width=True):
                            duplicate_session(int(row["id"]), new_d)
                            st.success(f"Session dupliquée le {new_d.strftime('%-d %B %Y')} !")
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : SAISIR UNE SESSION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "➕ Saisir une session":
    st.title("➕ Saisir une session")
    clients_df = get_clients()

    if clients_df.empty:
        st.warning("Aucun client enregistré. Va dans 👥 Clients pour en créer un.")
    else:
        with st.form("session_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            sel_name = c1.selectbox("Client", clients_df["name"].tolist())
            work_date = c2.date_input("Date", value=date.today())
            crow = clients_df[clients_df["name"] == sel_name].iloc[0]
            c3, c4 = st.columns(2)
            hours = c3.number_input("Heures", 0.25, 24.0, 1.0, 0.25)
            rate  = c4.number_input(f"Taux ({CURRENCY}/h)", 0.0, value=float(crow["default_rate"]), step=5.0)
            note  = st.text_input("Note (optionnel)")
            tva   = float(crow.get("tva", 0.0))
            ht    = hours * rate
            ttc   = ht * (1 + tva / 100)
            if tva > 0:
                st.info(f"HT : **{fmt_money(ht)}** · TVA {tva:.0f}% · TTC : **{fmt_money(ttc)}**")
            else:
                st.info(f"Total : **{fmt_money(ht)}**")
            if st.form_submit_button("✅ Enregistrer", use_container_width=True):
                add_session(int(crow["id"]), work_date, hours, rate, note)
                st.success(f"Session enregistrée pour {sel_name} le {work_date.strftime('%-d %B %Y')} !")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : SESSIONS RÉCURRENTES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔁 Sessions récurrentes":
    st.title("🔁 Sessions récurrentes")
    st.markdown("Crée automatiquement une session chaque semaine pour un jour donné.")
    clients_df = get_clients()

    if clients_df.empty:
        st.warning("Crée d'abord un client dans 👥 Clients.")
    else:
        with st.form("recur_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            sel_name = c1.selectbox("Client", clients_df["name"].tolist())
            weekday  = c2.selectbox("Jour de la semaine", range(7), format_func=lambda x: WEEKDAY_FR[x])
            crow = clients_df[clients_df["name"] == sel_name].iloc[0]
            c3, c4 = st.columns(2)
            start = c3.date_input("Début", value=date.today())
            end   = c4.date_input("Fin",   value=date.today() + timedelta(weeks=4))
            c5, c6 = st.columns(2)
            hours = c5.number_input("Heures", 0.25, 24.0, 1.0, 0.25)
            rate  = c6.number_input(f"Taux ({CURRENCY}/h)", 0.0, value=float(crow["default_rate"]), step=5.0)
            note  = st.text_input("Note (optionnel)")

            if st.form_submit_button("🔁 Créer les sessions", use_container_width=True):
                if end < start:
                    st.error("La date de fin doit être après la date de début.")
                else:
                    n = add_recurring_sessions(int(crow["id"]), hours, rate, note, weekday, start, end)
                    st.success(f"✅ {n} session(s) créée(s) chaque {WEEKDAY_FR[weekday]} !")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : CLIENTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👥 Clients":
    st.title("👥 Gestion des clients")

    with st.expander("➕ Ajouter un client", expanded=True):
        with st.form("add_client_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            new_name  = c1.text_input("Nom *")
            new_rate  = c2.number_input(f"Taux ({CURRENCY}/h)", 0.0, value=50.0, step=5.0)
            new_tva   = c3.number_input("TVA (%)", 0.0, 100.0, 0.0, step=1.0)
            new_color = c4.color_picker("Couleur", "#4A90E2")
            if st.form_submit_button("Ajouter", use_container_width=True):
                if not new_name.strip():
                    st.error("Le nom est obligatoire.")
                else:
                    ok, err = add_client(new_name.strip(), new_color, new_rate, new_tva)
                    if ok: st.success(f"Client **{new_name}** ajouté !"); st.rerun()
                    else:  st.error(err)

    st.divider()
    clients_df = get_clients()
    if clients_df.empty:
        st.info("Aucun client pour l'instant.")
    else:
        for _, row in clients_df.iterrows():
            tva_val = float(row.get("tva", 0.0))
            with st.expander(f"● {row['name']} — {row['default_rate']}{CURRENCY}/h"):
                with st.form(f"edit_{row['id']}"):
                    c1, c2, c3, c4 = st.columns(4)
                    upd_name  = c1.text_input("Nom",    value=row["name"])
                    upd_rate  = c2.number_input("Taux",  value=float(row["default_rate"]), step=5.0)
                    upd_tva   = c3.number_input("TVA %", value=tva_val, step=1.0)
                    upd_color = c4.color_picker("Couleur", value=row["color"])
                    cs, cd = st.columns(2)
                    if cs.form_submit_button("💾 Enregistrer", use_container_width=True):
                        update_client(int(row["id"]), upd_name, upd_color, upd_rate, upd_tva)
                        st.success("Mis à jour !"); st.rerun()
                    if cd.form_submit_button("🗑️ Supprimer", use_container_width=True):
                        delete_client(int(row["id"]))
                        st.warning(f"{row['name']} supprimé."); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : RÉCAPITULATIF
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Récapitulatif":
    st.title("📊 Récapitulatif")
    sessions_df  = get_sessions_full()
    summary_df   = get_monthly_summary()

    if sessions_df.empty:
        st.info("Aucune session enregistrée.")
    else:
        total_hours = sessions_df["hours"].sum()
        total_euros = sessions_df["total"].sum()
        k1,k2,k3,k4 = st.columns(4)
        k1.metric("⏱ Heures totales",  fmt_hours(total_hours))
        k2.metric(f"💶 Revenus totaux HT", fmt_money(total_euros))
        k3.metric("👥 Clients",         sessions_df["client"].nunique())
        k4.metric("📋 Sessions",        len(sessions_df))

        st.divider()

        # Camembert par client (global)
        st.subheader("🥧 Répartition par client")
        pie = sessions_df.groupby(["client","color"])["total"].sum().reset_index()
        tot = pie["total"].sum()
        pcols = st.columns(len(pie))
        for i, (_, row) in enumerate(pie.iterrows()):
            pct = row["total"]/tot*100
            pcols[i].markdown(
                f"<div style='text-align:center'>"
                f"<span class='tag' style='background:{row.color}'>{row['client']}</span><br>"
                f"<b>{fmt_money(row['total'])}</b><br>"
                f"<span style='font-size:.8rem;color:{SUBTEXT}'>{pct:.1f}%</span></div>",
                unsafe_allow_html=True)

        st.divider()

        # Par mois
        st.subheader("Par mois")
        for mois in summary_df["mois"].unique():
            md = summary_df[summary_df["mois"]==mois]
            label = pd.to_datetime(mois+"-01").strftime("%B %Y").capitalize()
            mh = md["total_heures"].sum(); me = md["total_euros"].sum()
            with st.expander(f"📆 {label} — {fmt_hours(mh)} · {fmt_money(me)}"):
                for _, row in md.iterrows():
                    c1,c2,c3 = st.columns([3,1,1])
                    c1.markdown(f"<span class='tag' style='background:{row.color}'>{row['client']}</span>", unsafe_allow_html=True)
                    c2.write(fmt_hours(row["total_heures"]))
                    c3.write(fmt_money(row["total_euros"]))

        st.divider()

        # Par client avec TVA
        st.subheader("Par client")
        client_summary = sessions_df.groupby(["client","color","tva"]).agg(
            Heures=("hours","sum"), Revenus=("total","sum"), Sessions=("id","count")
        ).reset_index()
        for _, row in client_summary.iterrows():
            c1,c2,c3,c4,c5 = st.columns([3,1,1,1,1])
            c1.markdown(f"<span class='tag' style='background:{row.color}'>{row['client']}</span>", unsafe_allow_html=True)
            c2.write(fmt_hours(row["Heures"]))
            c3.write(fmt_money(row["Revenus"]))
            tva = float(row.get("tva", 0.0))
            if tva > 0:
                c4.write(f"TVA {tva:.0f}%")
                c5.write(fmt_money(row["Revenus"] * (1 + tva/100)))
            else:
                c4.write("—")
                c5.write(f"📋 {row['Sessions']}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : EXPORT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📤 Export":
    st.title("📤 Export")
    sessions_df = get_sessions_full()

    if sessions_df.empty:
        st.info("Aucune donnée à exporter.")
    else:
        clients_df = get_clients()
        c1, c2, c3 = st.columns(3)
        filter_client = c1.multiselect("Filtrer par client", clients_df["name"].tolist())
        filter_month  = c2.selectbox("Mois", ["Tous"] + [f"{m:02d}" for m in range(1,13)],
                                     format_func=lambda x: "Tous" if x=="Tous" else MONTH_FR[int(x)-1])
        filter_year   = c3.selectbox("Année", ["Toutes"] + sorted(sessions_df["work_date"].dt.year.unique().tolist(), reverse=True))

        exp = sessions_df.copy()
        if filter_client: exp = exp[exp["client"].isin(filter_client)]
        if filter_month != "Tous": exp = exp[exp["work_date"].dt.month == int(filter_month)]
        if filter_year  != "Toutes": exp = exp[exp["work_date"].dt.year == int(filter_year)]

        exp["tva_amount"] = exp.apply(lambda r: r["total"] * r["tva"]/100, axis=1)
        exp["total_ttc"]  = exp["total"] + exp["tva_amount"]
        exp["work_date_fmt"] = exp["work_date"].dt.strftime("%d/%m/%Y")

        display = exp.rename(columns={
            "client":"Client","work_date_fmt":"Date","hours":"Heures",
            "rate":f"Taux ({CURRENCY}/h)","total":"Total HT","tva":"TVA %",
            "tva_amount":"Montant TVA","total_ttc":"Total TTC","note":"Note"
        })[["Client","Date","Heures",f"Taux ({CURRENCY}/h)","Total HT","TVA %","Montant TVA","Total TTC","Note"]]

        st.dataframe(display, use_container_width=True)
        st.markdown(f"**Total HT : {fmt_money(exp['total'].sum())} · Total TTC : {fmt_money(exp['total_ttc'].sum())}**")

        csv = display.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        st.download_button("⬇️ Télécharger CSV", csv, "timetracker_export.csv", "text/csv", use_container_width=True)

        # Facture simple par client
        st.divider()
        st.subheader("🧾 Générer une facture")
        sel_invoice_client = st.selectbox("Client à facturer", exp["client"].unique().tolist() if not exp.empty else [])
        if sel_invoice_client:
            inv = exp[exp["client"] == sel_invoice_client]
            ht_total  = inv["total"].sum()
            tva_total = inv["tva_amount"].sum()
            ttc_total = inv["total_ttc"].sum()
            inv_lines = ""
            for _, r in inv.iterrows():
                inv_lines += f"| {r['work_date_fmt']} | {r['hours']}h | {r['rate']:.2f} {CURRENCY} | {r['total']:.2f} {CURRENCY} | {r['note']} |\n"

            invoice_text = f"""# Facture — {sel_invoice_client}

**Date d'émission :** {date.today().strftime('%d/%m/%Y')}

| Date | Heures | Taux | Montant HT | Note |
|------|--------|------|-----------|------|
{inv_lines}
**Total HT : {ht_total:.2f} {CURRENCY}**
**TVA : {tva_total:.2f} {CURRENCY}**
**Total TTC : {ttc_total:.2f} {CURRENCY}**
"""
            st.markdown(invoice_text)
            st.download_button(
                "⬇️ Télécharger la facture (Markdown)",
                invoice_text.encode("utf-8"),
                f"facture_{sel_invoice_client.replace(' ','_')}.md",
                "text/markdown",
                use_container_width=True
            )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : PARAMÈTRES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Paramètres":
    st.title("⚙️ Paramètres")
    cfg = get_settings()

    with st.form("settings_form"):
        app_name  = st.text_input("Nom de l'application", value=cfg["app_name"])
        currency  = st.selectbox("Devise", ["€", "$", "CHF", "£", "CAD$"],
                                 index=["€","$","CHF","£","CAD$"].index(cfg.get("currency","€")))
        dark_mode = st.toggle("Mode sombre", value=cfg.get("dark_mode", False))
        if st.form_submit_button("💾 Enregistrer les paramètres", use_container_width=True):
            save_settings(app_name, currency, dark_mode)
            st.success("Paramètres sauvegardés ! Recharge la page pour voir les changements.")
            st.rerun()
