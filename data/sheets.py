import gspread
import pandas as pd
import os
import time
import streamlit as st
from google.oauth2.service_account import Credentials

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1dmalD519xdQzbi2Pef1kFsRj29PyyxEH6zTNcuV3aR4/edit"
WORKSHEET_NAME = "Arkusz1"

@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_file("credentials.json", scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

def get_worksheet():
    sh = get_gspread_client().open_by_url(SPREADSHEET_URL)
    try: return sh.worksheet(WORKSHEET_NAME)
    except: return sh.sheet1

def load_user_data(username):
    try:
        data = get_worksheet().get_all_records()
        df = pd.DataFrame(data)
        return df[df['Wlasciciel'] == username].to_dict('records') if 'Wlasciciel' in df.columns else []
    except: return []

def save_user_data(username, portfolio_list):
    ws = get_worksheet()
    try:
        all_df = pd.DataFrame(ws.get_all_records())
        others = all_df[all_df['Wlasciciel'] != username] if not all_df.empty else pd.DataFrame()
        new_user_df = pd.DataFrame(portfolio_list)
        new_user_df['Wlasciciel'] = username
        final = pd.concat([others, new_user_df], ignore_index=True)
        ws.clear()
        ws.update([final.columns.tolist()] + final.values.tolist())
        return True
    except: return False