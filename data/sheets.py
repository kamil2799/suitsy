import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

# Pozostaw linki bez zmian
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1dmalD519xdQzbi2Pef1kFsRj29PyyxEH6zTNcuV3aR4/edit"
WORKSHEET_NAME = "Arkusz1"

@st.cache_resource
def get_gspread_client():
    creds_info = st.secrets["gcp_service_account"]
 
    if "private_key" in creds_info:
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

def get_worksheet():
    try:
        sh = get_gspread_client().open_by_url(SPREADSHEET_URL)
        return sh.worksheet(WORKSHEET_NAME)
    except Exception as e:
        # Jeśli nie znajdzie po nazwie, bierze pierwszy arkusz
        sh = get_gspread_client().open_by_url(SPREADSHEET_URL)
        return sh.get_worksheet(0)

def load_user_data(username):
    try:
        ws = get_worksheet()
        data = ws.get_all_records()
        if not data:
            return []
            
        df = pd.DataFrame(data)
 
        if 'Wlasciciel' in df.columns:
            df['Wlasciciel_Lower'] = df['Wlasciciel'].astype(str).str.strip().str.lower()
            filtered_df = df[df['Wlasciciel_Lower'] == username.strip().lower()]
            return filtered_df.drop(columns=['Wlasciciel_Lower']).to_dict('records')
            
        return []
    except Exception as e:
        st.error(f"Błąd podczas ładowania danych: {e}")
        return []

def save_user_data(username, portfolio_list):
    try:
        ws = get_worksheet()
        all_data = ws.get_all_records()
        all_df = pd.DataFrame(all_data) if all_data else pd.DataFrame()
        
        if not all_df.empty and 'Wlasciciel' in all_df.columns:
            others = all_df[all_df['Wlasciciel'].astype(str).str.lower() != username.lower()]
        else:
            others = pd.DataFrame()

        new_user_df = pd.DataFrame(portfolio_list)
        new_user_df['Wlasciciel'] = username
        
        final = pd.concat([others, new_user_df], ignore_index=True)
        
        ws.clear()
        ws.update([final.columns.tolist()] + final.values.tolist())
        return True
    except Exception as e:
        st.error(f"Błąd podczas zapisu: {e}")
        return False
