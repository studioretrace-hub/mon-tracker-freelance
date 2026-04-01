import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURATION ---
FILE_DB = "data_facturation.csv"

def load_data():
    if os.path.exists(FILE_DB):
        return pd.read_csv(FILE_DB, parse_dates=['Date'])
    return pd.DataFrame(columns=['Date', 'Client', 'Heures', 'Taux', 'Total'])

def save_data(df):
    df.to_csv(FILE_DB, index=False)

# --- INTERFACE ---
st.set_page_config(page_title="My Freelance Tracker", layout="wide")
st.title("📊 Mon Calendrier de Facturation")

data = load_data()

# --- SIDEBAR : MODÈLES ET SAISIE ---
with st.sidebar:
    st.header("⚡ Saisie Rapide")
    
    # Gestion des modèles (mémoire session)
    if 'modeles' not in st.session_state:
        st.session_state.modeles = {"Standard": {"h": 3, "t": 30}}
    
    with st.expander("➕ Créer un modèle"):
        m_name = st.text_input("Nom du modèle")
        m_h = st.number_input("Heures", value=1)
        m_t = st.number_input("Taux horaire (€)", value=30)
        if st.button("Enregistrer modèle"):
            st.session_state.modeles[m_name] = {"h": m_h, "t": m_t}

    st.divider()
    
    # Formulaire d'ajout
    choix_dates = st.date_input("Sélectionner les jours", value=[datetime.now()], help="Maintenez Ctrl/Cmd pour plusieurs jours")
    client = st.text_input("Tag Client", value="Client A")
    mod_choisi = st.selectbox("Appliquer un modèle", list(st.session_state.modeles.keys()))
    
    if st.button("Ajouter à la facturation"):
        new_entries = []
        h = st.session_state.modeles[mod_choisi]["h"]
        t = st.session_state.modeles[mod_choisi]["t"]
        
        # Gestion multi-dates
        dates_list = choix_dates if isinstance(choix_dates, list) else [choix_dates]
        for d in dates_list:
            new_entries.append({
                'Date': d, 'Client': client, 'Heures': h, 'Taux': t, 'Total': h * t
            })
        
        data = pd.concat([data, pd.DataFrame(new_entries)], ignore_index=True)
        save_data(data)
        st.success("Ajouté !")

# --- DASHBOARD PRINCIPAL ---
if not data.empty:
    data['Date'] = pd.to_datetime(data['Date'])
    data['Mois'] = data['Date'].dt.strftime('%Y-%m')

    # Filtres
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        mois_focus = st.selectbox("Filtrer par Mois", sorted(data['Mois'].unique(), reverse=True))
    with col_f2:
        client_focus = st.selectbox("Filtrer par Client", ["Tous"] + list(data['Client'].unique()))

    # Calculs
    df_filtre = data[data['Mois'] == mois_focus]
    if client_focus != "Tous":
        df_filtre = df_filtre[df_filtre['Client'] == client_focus]

    # Affichage des métriques
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Période", f"{df_filtre['Total'].sum()} €")
    m2.metric("Heures Totales", f"{df_filtre['Heures'].sum()} h")
    m3.metric("Nombre de jours", len(df_filtre))

    st.divider()
    st.subheader("Historique détaillé")
    st.dataframe(df_filtre[['Date', 'Client', 'Heures', 'Taux', 'Total']].sort_values('Date'), use_container_width=True)
    
    if st.button("Supprimer tout l'historique (Danger)"):
        if os.path.exists(FILE_DB):
            os.remove(FILE_DB)
            st.rerun()
else:
    st.info("Aucune donnée enregistrée. Utilisez la barre latérale pour commencer.")
