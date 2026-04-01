import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_calendar import calendar
import os

# --- CONFIGURATION ---
FILE_DB = "data_facturation.csv"

def load_data():
    if os.path.exists(FILE_DB):
        try:
            df = pd.read_csv(FILE_DB)
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            return df.dropna(subset=['Date'])
        except:
            return pd.DataFrame(columns=['Date', 'Client', 'Heures', 'Taux', 'Total'])
    return pd.DataFrame(columns=['Date', 'Client', 'Heures', 'Taux', 'Total'])

def save_data(df):
    df.to_csv(FILE_DB, index=False, date_format='%Y-%m-%d')

# --- INTERFACE ---
st.set_page_config(page_title="Freelance Calendar", layout="wide")
st.title("📅 Mon Calendrier de Travail")

data = load_data()

# --- INITIALISATION SESSION ---
if 'selected_dates' not in st.session_state:
    st.session_state.selected_dates = []
if 'modeles' not in st.session_state:
    st.session_state.modeles = {"Standard (3h)": {"h": 3, "t": 30}, "Journée (7h)": {"h": 7, "t": 30}}

# --- PRÉPARATION DES ÉVÉNEMENTS DU CALENDRIER ---
calendar_events = []

# 1. Ajouter les jours DÉJÀ ENREGISTRÉS (en Bleu)
for _, row in data.iterrows():
    calendar_events.append({
        "title": f"✅ {row['Client']}",
        "start": row['Date'].strftime('%Y-%m-%d'),
        "allDay": True,
        "color": "#3D5AFE" # Bleu
    })

# 2. Ajouter les jours EN COURS DE SÉLECTION (en Orange pour la surbrillance)
for d_str in st.session_state.selected_dates:
    calendar_events.append({
        "title": "SÉLECTIONNÉ",
        "start": d_str,
        "allDay": True,
        "color": "#FF9800" # Orange
    })

# --- COLONNE GAUCHE : LE CALENDRIER ---
col_cal, col_form = st.columns([2, 1])

with col_cal:
    st.markdown("### 1. Cliquez sur les jours (Passés ou Futur)")
    
    calendar_options = {
        "editable": False,
        "selectable": True,
        "headerToolbar": {"left": "today prev,next", "center": "title", "right": ""},
        "locale": "fr" # Calendrier en Français
    }

    state = calendar(events=calendar_events, options=calendar_options, key="calendar")
    
    # Gestion du clic pour ajouter/retirer de la surbrillance
    if state.get("dateClick"):
        clicked_date = state["dateClick"]["date"].split("T")[0]
        if clicked_date not in st.session_state.selected_dates:
            st.session_state.selected_dates.append(clicked_date)
        else:
            st.session_state.selected_dates.remove(clicked_date)
        st.rerun()

# --- COLONNE DROITE : ACTIONS & RÉCAP ---
with col_form:
    st.markdown("### 2. Valider la sélection")
    
    if st.session_state.selected_dates:
        st.info(f"orange : {len(st.session_state.selected_dates)} jour(s) en attente")
        
        client_tag = st.text_input("Nom du Client", value="Client A")
        mod_choisi = st.selectbox("Modèle de prestation", list(st.session_state.modeles.keys()))
        
        if st.button("💾 Enregistrer la sélection", use_container_width=True):
            h = st.session_state.modeles[mod_choisi]["h"]
            t = st.session_state.modeles[mod_choisi]["t"]
            
            new_entries = []
            for d_str in st.session_state.selected_dates:
                new_entries.append({
                    'Date': pd.to_datetime(d_str),
                    'Client': client_tag,
                    'Heures': h,
                    'Taux': t,
                    'Total': h * t
                })
            
            data = pd.concat([data, pd.DataFrame(new_entries)], ignore_index=True)
            save_data(data)
            st.session_state.selected_dates = [] # On vide la surbrillance
            st.success("Données enregistrées !")
            st.rerun()
            
        if st.button("❌ Annuler la sélection", use_container_width=True):
            st.session_state.selected_dates = []
            st.rerun()
    else:
        st.write("Cliquez sur des dates à gauche pour les cocher.")

# --- SECTION BAS : TOTAL TEMPS RÉEL ---
st.divider()
if not data.empty:
    # Calcul du mois en cours
    data['Mois'] = data['Date'].dt.strftime('%Y-%m')
    current_month = datetime.now().strftime('%Y-%m')
    df_mois = data[data['Mois'] == current_month]
    
    st.subheader(f"💰 Récapitulatif du mois ({datetime.now().strftime('%m/%Y')})")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("À facturer ce mois", f"{df_mois['Total'].sum():.2f} €")
    m2.metric("Heures totales", f"{df_mois['Heures'].sum():.1f} h")
    m3.metric("Jours travaillés", len(df_mois))
    
    with st.expander("⚙️ Gérer les données enregistrées"):
        st.dataframe(data.sort_values('Date', ascending=False), use_container_width=True)
        if st.button("🗑️ Vider TOUT l'historique"):
            if os.path.exists(
