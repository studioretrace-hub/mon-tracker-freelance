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

# --- COLONNE GAUCHE : LE CALENDRIER ---
col_cal, col_form = st.columns([2, 1])

with col_cal:
    st.markdown("### 1. Cliquez sur les jours travaillés")
    
    # Configuration du calendrier
    calendar_options = {
        "editable": True,
        "selectable": True,
        "headerToolbar": {"left": "today prev,next", "center": "title", "right": ""},
    }
    
    # On affiche les événements déjà enregistrés en bleu
    calendar_events = []
    for _, row in data.iterrows():
        calendar_events.append({
            "title": f"✅ {row['Client']}",
            "start": row['Date'].strftime('%Y-%m-%d'),
            "end": row['Date'].strftime('%Y-%m-%d'),
            "color": "#3D5AFE"
        })

    state = calendar(events=calendar_events, options=calendar_options, key="calendar")
    
    # Capture du clic sur le calendrier
    if state.get("dateClick"):
        clicked_date = state["dateClick"]["date"].split("T")[0]
        if clicked_date not in st.session_state.selected_dates:
            st.session_state.selected_dates.append(clicked_date)
        else:
            st.session_state.selected_dates.remove(clicked_date)

# --- COLONNE DROITE : ACTIONS & RÉCAP ---
with col_form:
    st.markdown("### 2. Valider la sélection")
    
    if st.session_state.selected_dates:
        st.write(f"**Jours sélectionnés ({len(st.session_state.selected_dates)}) :**")
        st.caption(", ".join(st.session_state.selected_dates))
        
        client_tag = st.text_input("Client", value="Client A")
        mod_choisi = st.selectbox("Modèle", list(st.session_state.modeles.keys()))
        
        if st.button("Enregistrer ces jours"):
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
            st.session_state.selected_dates = [] # Reset
            st.success("Enregistré !")
            st.rerun()
            
        if st.button("Vider la sélection"):
            st.session_state.selected_dates = []
            st.rerun()
    else:
        st.info("Cliquez sur des cases du calendrier à gauche pour commencer.")

# --- SECTION BAS : TOTAL TEMPS RÉEL ---
st.divider()
if not data.empty:
    data['Mois'] = data['Date'].dt.strftime('%Y-%m')
    current_month = datetime.now().strftime('%Y-%m')
    
    df_mois = data[data['Mois'] == current_month]
    
    st.subheader(f"💰 Total {datetime.now().strftime('%B %Y')}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Gains du mois", f"{df_mois['Total'].sum():.2f} €")
    m2.metric("Heures travaillées", f"{df_mois['Heures'].sum():.1f} h")
    m3.metric("Nombre de missions", len(df_mois))
    
    with st.expander("Voir le détail des lignes"):
        st.table(data.sort_values('Date', ascending=False).head(10))
