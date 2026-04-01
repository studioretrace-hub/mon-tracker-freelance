import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import os

# --- CONFIGURATION ---
FILE_DB = "data_facturation.csv"

def load_data():
    if os.path.exists(FILE_DB):
        try:
            df = pd.read_csv(FILE_DB)
            # Conversion forcée en format date
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            # Nettoyage des lignes corrompues
            df = df.dropna(subset=['Date'])
            return df
        except:
            return pd.DataFrame(columns=['Date', 'Client', 'Heures', 'Taux', 'Total'])
    return pd.DataFrame(columns=['Date', 'Client', 'Heures', 'Taux', 'Total'])

def save_data(df):
    # Sauvegarde propre au format YYYY-MM-DD
    df.to_csv(FILE_DB, index=False, date_format='%Y-%m-%d')

# --- INTERFACE ---
st.set_page_config(page_title="Freelance Tracker", layout="wide")
st.title("📊 Mon Calendrier de Facturation")

data = load_data()

# --- SIDEBAR : MODÈLES ET SAISIE ---
with st.sidebar:
    st.header("⚡ Saisie Rapide")
    
    # Gestion des modèles en mémoire
    if 'modeles' not in st.session_state:
        st.session_state.modeles = {"Standard (3h)": {"h": 3, "t": 30}}
    
    with st.expander("➕ Créer un nouveau modèle"):
        m_name = st.text_input("Nom du modèle (ex: Journée pleine)")
        m_h = st.number_input("Nombre d'heures", value=7.0, step=0.5)
        m_t = st.number_input("Taux horaire (€)", value=30, step=5)
        if st.button("Enregistrer ce modèle"):
            if m_name:
                st.session_state.modeles[m_name] = {"h": m_h, "t": m_t}
                st.success(f"Modèle '{m_name}' ajouté !")

    st.divider()
    
    # --- SÉLECTEUR DE JOURS MULTIPLES ---
    st.subheader("📅 Cocher les jours")
    today = datetime.now()
    
    # Génération des jours du mois en cours
    num_days = calendar.monthrange(today.year, today.month)[1]
    jours_obj = [datetime(today.year, today.month, d) for d in range(1, num_days + 1)]
    options_jours = [d.strftime('%d/%m/%Y') for d in jours_obj]
    
    jours_selectionnes_str = st.multiselect(
        "Sélectionnez un ou plusieurs jours :",
        options=options_jours,
        default=[today.strftime('%d/%m/%Y')]
    )
    
    client_tag = st.text_input("Tag Client", value="Client A")
    mod_choisi = st.selectbox("Choisir un modèle", list(st.session_state.modeles.keys()))
    
    if st.button("🚀 Ajouter à la facturation"):
        if not jours_selectionnes_str:
            st.error("Sélectionnez au moins un jour !")
        else:
            h = st.session_state.modeles[mod_choisi]["h"]
            t = st.session_state.modeles[mod_choisi]["t"]
            
            new_entries = []
            for date_str in jours_selectionnes_str:
                d_obj = datetime.strptime(date_str, '%d/%m/%Y')
                new_entries.append({
                    'Date': d_obj, 
                    'Client': client_tag, 
                    'Heures': h, 
                    'Taux': t, 
                    'Total': h * t
                })
            
            new_df = pd.DataFrame(new_entries)
            data = pd.concat([data, new_df], ignore_index=True)
            save_data(data)
            st.success(f"Ajouté : {len(jours_selectionnes_str)} jour(s)")
            st.rerun()

# --- DASHBOARD PRINCIPAL ---
if not data.empty:
    # On s'assure que le mois est bien calculé pour le filtre
    data['Mois'] = data['Date'].dt.strftime('%Y-%m')

    # Filtres de vue
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        liste_mois = sorted(data['Mois'].unique(), reverse=True)
        mois_focus = st.selectbox("📅 Filtrer par mois", liste_mois)
    with col_f2:
        liste_clients = ["Tous"] + list(data['Client'].unique())
        client_focus = st.selectbox("👤 Filtrer par client", liste_clients)

    # Application des filtres
    df_filtre = data[data['Mois'] == mois_focus]
    if client_focus != "Tous":
        df_filtre = df_filtre[df_filtre['Client'] == client_focus]

    # Affichage des métriques financières
    m1, m2, m3 = st.columns(3)
    m1.metric("Total à facturer", f"{df_filtre['Total'].sum():,.2f} €".replace(',', ' '))
    m2.metric("Heures cumulées", f"{df_filtre['Heures'].sum():.1f} h")
    m3.metric("Jours travaillés", len(df_filtre))

    st.divider()
    
    # Affichage du tableau
    st.subheader("Détail des prestations")
    df_display = df_filtre.copy()
    df_display['Date'] = df_display['Date'].dt.strftime('%d/%m/%Y')
    st.dataframe(
        df_display[['Date', 'Client', 'Heures', 'Taux', 'Total']].sort_values('Date', ascending=False), 
        use_container_width=True
    )
    
    # Bouton de nettoyage
    with st.expander("⚙️ Options avancées"):
        if st.button("🗑️ Vider tout l'historique"):
            if os.path.exists(FILE_DB):
                os.remove(FILE_DB)
                st.rerun()
else:
    st.info("👋 Bienvenue ! Utilisez la barre latérale pour ajouter vos premières heures de travail.")
