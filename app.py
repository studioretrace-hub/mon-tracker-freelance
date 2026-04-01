import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURATION ---
FILE_DB = "data_facturation.csv"

def load_data():
    if os.path.exists(FILE_DB):
        try:
            df = pd.read_csv(FILE_DB)
            # On force la conversion de la colonne Date proprement
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            # On supprime les lignes où la date est devenue invalide (NaT)
            df = df.dropna(subset=['Date'])
            return df
        except:
            return pd.DataFrame(columns=['Date', 'Client', 'Heures', 'Taux', 'Total'])
    return pd.DataFrame(columns=['Date', 'Client', 'Heures', 'Taux', 'Total'])

def save_data(df):
    # On sauvegarde au format ISO standard pour éviter les erreurs futures
    df.to_csv(FILE_DB, index=False, date_format='%Y-%m-%d')

# --- INTERFACE ---
st.set_page_config(page_title="My Freelance Tracker", layout="wide")
st.title("📊 Mon Calendrier de Facturation")

data = load_data()

# --- SIDEBAR : MODÈLES ET SAISIE ---
with st.sidebar:
    st.header("⚡ Saisie Rapide")
    
    if 'modeles' not in st.session_state:
        st.session_state.modeles = {"Standard": {"h": 3, "t": 30}}
    
    with st.expander("➕ Créer un modèle"):
        m_name = st.text_input("Nom du modèle")
        m_h = st.number_input("Heures", value=1, step=1)
        m_t = st.number_input("Taux horaire (€)", value=30, step=5)
        if st.button("Enregistrer modèle"):
            if m_name:
                st.session_state.modeles[m_name] = {"h": m_h, "t": m_t}
                st.success(f"Modèle '{m_name}' créé !")

    st.divider()
    
    choix_dates = st.date_input("Sélectionner les jours", value=datetime.now())
    client = st.text_input("Tag Client", value="Client A")
    mod_choisi = st.selectbox("Appliquer un modèle", list(st.session_state.modeles.keys()))
    
    if st.button("Ajouter à la facturation"):
        h = st.session_state.modeles[mod_choisi]["h"]
        t = st.session_state.modeles[mod_choisi]["t"]
        
        # Gestion si date unique ou liste (selon le widget)
        if isinstance(choix_dates, list):
            dates_list = choix_dates
        else:
            dates_list = [choix_dates]
            
        new_entries = []
        for d in dates_list:
            new_entries.append({
                'Date': d, 'Client': client, 'Heures': h, 'Taux': t, 'Total': h * t
            })
        
        data = pd.concat([data, pd.DataFrame(new_entries)], ignore_index=True)
        save_data(data)
        st.success("Ajouté ! Rafraîchissement...")
        st.rerun()

# --- DASHBOARD PRINCIPAL ---
if not data.empty:
    # Création du mois pour le filtrage
    data['Mois'] = data['Date'].dt.strftime('%Y-%m')

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        mois_focus = st.selectbox("Filtrer par Mois", sorted(data['Mois'].unique(), reverse=True))
    with col_f2:
        client_focus = st.selectbox("Filtrer par Client", ["Tous"] + list(data['Client'].unique()))

    df_filtre = data[data['Mois'] == mois_focus]
    if client_focus != "Tous":
        df_filtre = df_filtre[df_filtre['Client'] == client_focus]

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Période", f"{df_filtre['Total'].sum():.2f} €")
    m2.metric("Heures Totales", f"{df_filtre['Heures'].sum():.1f} h")
    m3.metric("Jours travaillés", len(df_filtre))

    st.divider()
    st.subheader("Historique")
    # On affiche la date proprement
    df_display = df_filtre.copy()
    df_display['Date'] = df_display['Date'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_display[['Date', 'Client', 'Heures', 'Taux', 'Total']].sort_values('Date'), use_container_width=True)
    
    if st.button("🗑️ Vider tout l'historique"):
        if os.path.exists(FILE_DB):
            os.remove(FILE_DB)
            st.rerun()
else:
    st.info("Aucune donnée enregistrée. Utilisez la barre latérale pour commencer.")
