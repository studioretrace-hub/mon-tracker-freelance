import streamlit as st
import pandas as pd
import calendar
from datetime import date, timedelta
import io

from database import (
    init_db, add_client, get_clients, update_client, delete_client,
    add_session, get_sessions_full, delete_session, get_monthly_summary
)

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()

st.set_page_config(
    page_title="Time Tracker",
    page_icon="🗓️",
    layout="wide"
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { padding-top: 1rem; }
    div[data-testid="stMetric"] {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 12px 16px;
        border-left: 4px solid #4A90E2;
    }
    .calendar-day {
        border-radius: 8px;
        padding: 6px;
        text-align: center;
        font-size: 0.85rem;
        margin: 2px;
        min-height: 60px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    h1 { color: #2c3e50; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🗓️ Time Tracker")
    page = st.radio(
        "Navigation",
        ["📅 Calendrier", "➕ Saisir une session", "👥 Clients", "📊 Récapitulatif", "📤 Export"],
        label_visibility="collapsed"
    )
    st.divider()
    clients_df = get_clients()
    if not clients_df.empty:
        st.markdown("**Clients actifs**")
        for _, row in clients_df.iterrows():
            st.markdown(
                f"<span style='background:{row.color};border-radius:4px;"
                f"padding:2px 8px;color:white;font-size:0.8rem'>● {row['name']}</span>",
                unsafe_allow_html=True
            )

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : CALENDRIER
# ══════════════════════════════════════════════════════════════════════════════
if page == "📅 Calendrier":
    st.title("📅 Calendrier")

    sessions_df = get_sessions_full()

    # Sélecteur mois/année
    col1, col2, _ = st.columns([1, 1, 4])
    today = date.today()
    selected_month = col1.selectbox(
        "Mois",
        range(1, 13),
        index=today.month - 1,
        format_func=lambda m: calendar.month_name[m].capitalize()
    )
    selected_year = col2.number_input("Année", min_value=2020, max_value=2030, value=today.year)

    # Filtrer les sessions du mois
    if not sessions_df.empty:
        mask = (sessions_df["work_date"].dt.month == selected_month) & \
               (sessions_df["work_date"].dt.year == selected_year)
        month_sessions = sessions_df[mask].copy()
    else:
        month_sessions = pd.DataFrame()

    # Construire le calendrier
    cal = calendar.monthcalendar(selected_year, selected_month)
    day_names = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

    # En-têtes
    cols = st.columns(7)
    for i, dn in enumerate(day_names):
        cols[i].markdown(
            f"<div style='text-align:center;font-weight:bold;color:#888;font-size:0.8rem'>{dn}</div>",
            unsafe_allow_html=True
        )

    # Cellules
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown("<div style='min-height:70px'></div>", unsafe_allow_html=True)
                    continue

                day_date = date(selected_year, selected_month, day)
                is_today = day_date == today

                # Sessions ce jour
                if not month_sessions.empty:
                    day_sessions = month_sessions[month_sessions["work_date"].dt.date == day_date]
                else:
                    day_sessions = pd.DataFrame()

                # Style
                border = "3px solid #2c3e50" if is_today else "1px solid #e0e0e0"
                bg = "#fff"

                # Couleur dominante si plusieurs clients
                color_dots = ""
                total_day = ""
                if not day_sessions.empty:
                    bg = "#f0f7ff"
                    total_h = day_sessions["hours"].sum()
                    total_e = day_sessions["total"].sum()
                    total_day = f"<div style='font-size:0.7rem;color:#2c3e50'><b>{total_h:.1f}h</b> · {total_e:.0f}€</div>"
                    for _, s in day_sessions.iterrows():
                        color_dots += f"<span style='background:{s.color};border-radius:3px;display:inline-block;width:10px;height:10px;margin:1px'></span>"

                st.markdown(f"""
                <div style='border:{border};background:{bg};border-radius:8px;
                            padding:6px;text-align:center;min-height:70px'>
                    <div style='font-weight:{"bold" if is_today else "normal"};font-size:0.9rem'>{day}</div>
                    {color_dots}
                    {total_day}
                </div>
                """, unsafe_allow_html=True)

    # Légende du mois
    if not month_sessions.empty:
        st.divider()
        st.markdown("**Sessions du mois**")
        for _, row in month_sessions.iterrows():
            c1, c2, c3, c4, c5 = st.columns([1.5, 2, 1, 1, 0.5])
            c1.markdown(f"<span style='background:{row.color};color:white;border-radius:4px;padding:2px 8px;font-size:0.8rem'>{row['client']}</span>", unsafe_allow_html=True)
            c2.write(row["work_date"].strftime("%-d %B %Y"))
            c3.write(f"⏱ {row['hours']}h")
            c4.write(f"💶 {row['total']:.2f}€")
            if c5.button("🗑️", key=f"del_{row['id']}"):
                delete_session(int(row["id"]))
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : SAISIR UNE SESSION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "➕ Saisir une session":
    st.title("➕ Saisir une session")

    clients_df = get_clients()

    if clients_df.empty:
        st.warning("Aucun client enregistré. Commence par créer un client dans l'onglet 👥 Clients.")
    else:
        with st.form("session_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            client_names = clients_df["name"].tolist()
            selected_client_name = col1.selectbox("Client", client_names)
            work_date = col2.date_input("Date", value=date.today())

            client_row = clients_df[clients_df["name"] == selected_client_name].iloc[0]
            default_rate = float(client_row["default_rate"])

            col3, col4 = st.columns(2)
            hours = col3.number_input("Heures travaillées", min_value=0.25, max_value=24.0, value=1.0, step=0.25)
            rate = col4.number_input("Taux horaire (€/h)", min_value=0.0, value=default_rate, step=5.0)

            note = st.text_input("Note (optionnel)", placeholder="Ex: réunion kick-off, livraison maquette...")

            total_preview = hours * rate
            st.info(f"💶 Total : **{total_preview:.2f} €** pour {hours}h à {rate}€/h")

            submitted = st.form_submit_button("✅ Enregistrer", use_container_width=True)
            if submitted:
                client_id = int(client_row["id"])
                add_session(client_id, work_date, hours, rate, note)
                st.success(f"Session enregistrée pour {selected_client_name} le {work_date.strftime('%-d %B %Y')} !")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : CLIENTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👥 Clients":
    st.title("👥 Gestion des clients")

    # Formulaire ajout
    with st.expander("➕ Ajouter un nouveau client", expanded=True):
        with st.form("add_client_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            new_name = col1.text_input("Nom du client *")
            new_rate = col2.number_input("Taux horaire par défaut (€/h)", min_value=0.0, value=50.0, step=5.0)
            new_color = col3.color_picker("Couleur", value="#4A90E2")
            submitted = st.form_submit_button("Ajouter le client", use_container_width=True)
            if submitted:
                if not new_name.strip():
                    st.error("Le nom du client est obligatoire.")
                else:
                    ok, err = add_client(new_name.strip(), new_color, new_rate)
                    if ok:
                        st.success(f"Client **{new_name}** ajouté !")
                        st.rerun()
                    else:
                        st.error(err)

    st.divider()

    # Liste des clients
    clients_df = get_clients()
    if clients_df.empty:
        st.info("Aucun client pour l'instant.")
    else:
        st.markdown("**Clients existants**")
        for _, row in clients_df.iterrows():
            with st.expander(f"● {row['name']}", expanded=False):
                with st.form(f"edit_{row['id']}"):
                    c1, c2, c3 = st.columns(3)
                    upd_name = c1.text_input("Nom", value=row["name"])
                    upd_rate = c2.number_input("Taux (€/h)", value=float(row["default_rate"]), step=5.0)
                    upd_color = c3.color_picker("Couleur", value=row["color"])
                    col_save, col_del = st.columns(2)
                    if col_save.form_submit_button("💾 Enregistrer", use_container_width=True):
                        update_client(int(row["id"]), upd_name, upd_color, upd_rate)
                        st.success("Mis à jour !")
                        st.rerun()
                    if col_del.form_submit_button("🗑️ Supprimer", use_container_width=True):
                        delete_client(int(row["id"]))
                        st.warning(f"Client {row['name']} supprimé.")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : RÉCAPITULATIF
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Récapitulatif":
    st.title("📊 Récapitulatif")

    sessions_df = get_sessions_full()
    summary_df = get_monthly_summary()

    if sessions_df.empty:
        st.info("Aucune session enregistrée pour l'instant.")
    else:
        # KPIs globaux
        total_hours = sessions_df["hours"].sum()
        total_euros = sessions_df["total"].sum()
        nb_clients = sessions_df["client"].nunique()
        nb_sessions = len(sessions_df)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("⏱ Heures totales", f"{total_hours:.1f}h")
        k2.metric("💶 Revenus totaux", f"{total_euros:.2f}€")
        k3.metric("👥 Clients", nb_clients)
        k4.metric("📋 Sessions", nb_sessions)

        st.divider()

        # Récap par mois
        st.subheader("Par mois")
        if not summary_df.empty:
            months = summary_df["mois"].unique().tolist()
            for mois in months:
                mois_data = summary_df[summary_df["mois"] == mois]
                mois_label = pd.to_datetime(mois + "-01").strftime("%B %Y").capitalize()
                mois_total_h = mois_data["total_heures"].sum()
                mois_total_e = mois_data["total_euros"].sum()

                with st.expander(f"📆 {mois_label} — {mois_total_h:.1f}h · {mois_total_e:.2f}€"):
                    for _, row in mois_data.iterrows():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        col1.markdown(
                            f"<span style='background:{row.color};color:white;border-radius:4px;"
                            f"padding:3px 10px'>{row['client']}</span>",
                            unsafe_allow_html=True
                        )
                        col2.write(f"⏱ {row['total_heures']:.1f}h")
                        col3.write(f"💶 {row['total_euros']:.2f}€")

        st.divider()

        # Récap par client
        st.subheader("Par client")
        client_summary = sessions_df.groupby(["client", "color"]).agg(
            Heures=("hours", "sum"),
            Revenus=("total", "sum"),
            Sessions=("id", "count")
        ).reset_index()

        for _, row in client_summary.iterrows():
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.markdown(
                f"<span style='background:{row.color};color:white;border-radius:4px;"
                f"padding:3px 10px'>{row['client']}</span>",
                unsafe_allow_html=True
            )
            c2.write(f"⏱ {row['Heures']:.1f}h")
            c3.write(f"💶 {row['Revenus']:.2f}€")
            c4.write(f"📋 {row['Sessions']} sessions")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : EXPORT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📤 Export":
    st.title("📤 Export des données")

    sessions_df = get_sessions_full()

    if sessions_df.empty:
        st.info("Aucune donnée à exporter.")
    else:
        export_df = sessions_df.copy()
        export_df["work_date"] = export_df["work_date"].dt.strftime("%d/%m/%Y")
        export_df = export_df.rename(columns={
            "client": "Client",
            "work_date": "Date",
            "hours": "Heures",
            "rate": "Taux (€/h)",
            "total": "Total (€)",
            "note": "Note"
        })[["Client", "Date", "Heures", "Taux (€/h)", "Total (€)", "Note"]]

        # Filtre optionnel
        clients_df = get_clients()
        col1, col2 = st.columns(2)
        filter_client = col1.multiselect(
            "Filtrer par client", 
            options=clients_df["name"].tolist(),
            default=[]
        )
        if filter_client:
            export_df = export_df[export_df["Client"].isin(filter_client)]

        st.dataframe(export_df, use_container_width=True)

        # CSV
        csv = export_df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        st.download_button(
            "⬇️ Télécharger CSV",
            data=csv,
            file_name="timetracker_export.csv",
            mime="text/csv",
            use_container_width=True
        )
