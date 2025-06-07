#!/usr/bin/env python3
# Utility functions for Google Sheets and Google Drive integration

import streamlit as st
import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
# PERBAIKAN: Impor MediaIoBaseUpload untuk upload dari memori
from googleapiclient.http import MediaIoBaseUpload
import io
import traceback

# Define the scopes required for Sheets and Drive API
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- Authentication --- 
def get_google_credentials():
    """Authenticates using service account credentials from Streamlit secrets."""
    try:
        creds_json = st.secrets["google_credentials"]
        creds = service_account.Credentials.from_service_account_info(creds_json, scopes=SCOPES)
        return creds
    except KeyError:
        return None
    except Exception as e:
        st.error(f"Error loading Google credentials: {e}")
        return None

def get_gspread_client(credentials):
    """Returns an authenticated gspread client."""
    if credentials:
        try:
            return gspread.authorize(credentials)
        except Exception as e:
            st.error(f"Error creating gspread client: {e}")
            return None
    return None

def get_drive_service(credentials):
    """Returns an authenticated Google Drive API service."""
    if credentials:
        try:
            return build("drive", "v3", credentials=credentials)
        except Exception as e:
            st.error(f"Error creating Google Drive service: {e}")
            return None
    return None

# --- Google Sheets Operations --- 
def append_to_sheet(gc, sheet_id, sheet_name, data_row):
    """Appends a row of data to the specified Google Sheet."""
    if not gc:
        st.error("Google Sheets client not available for appending data.")
        return False
    try:
        spreadsheet = gc.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        # Tugasnya cuma satu: tambahkan baris data.
        worksheet.append_row(data_row, value_input_option="USER_ENTERED")
        return True
    except gspread.exceptions.APIError as e:
        st.error(f"Google Sheets API Error: {e}. Check Sheet ID & permissions.", icon="🚨")
        return False
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{sheet_name}' not found.", icon="🚨")
        return False
    except Exception as e:
        st.error(f"Unexpected error appending to Sheet: {e}", icon="🚨")
        return False

# --- Google Drive Operations --- 
def upload_pdf_to_drive(drive_service, pdf_content, filename, folder_id):
    """Uploads PDF content to a specific Google Drive folder and returns the shareable link."""
    if not drive_service:
        st.error("Google Drive service not available for uploading PDF.")
        return None
    try:
        file_metadata = {
            "name": filename,
            "parents": [folder_id],
            "mimeType": "application/pdf"
        }

        # Buat objek BytesIO dari konten PDF (dalam format bytes)
        pdf_bytes_io = io.BytesIO(pdf_content)

        # PERBAIKAN UTAMA: Gunakan MediaIoBaseUpload untuk stream dari memori
        media = MediaIoBaseUpload(pdf_bytes_io, mimetype="application/pdf", resumable=True)

        # Upload file
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        web_view_link = file.get("webViewLink")
        return web_view_link

    except Exception as e:
        st.error(f"Error uploading PDF to Google Drive: {e}", icon="🚨")
        st.info(f"Attempted to upload '{filename}' to folder ID '{folder_id}'. Check folder ID and permissions.", icon="ℹ️")
        return None

def create_or_get_folder(drive_service, folder_name, parent_folder_id):
    """Checks if a folder exists in the parent folder. If not, creates it.
    Returns the folder ID."""
    if not drive_service:
        st.error("Google Drive service not available for folder operations.")
        return None
    try:
        # Query untuk mencari folder dengan nama spesifik di dalam parent folder
        query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])

        if files:
            # Jika folder sudah ada, kembalikan ID-nya
            st.info(f"Folder '{folder_name}' sudah ada. Menggunakan folder yang ada.")
            return files[0].get('id')
        else:
            # Jika folder tidak ada, buat folder baru
            st.info(f"Membuat folder baru: '{folder_name}'...")
            file_metadata = {
                'name': folder_name,
                'parents': [parent_folder_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = drive_service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')
            
    except Exception as e:
        st.error(f"Error saat membuat atau mencari folder di Google Drive: {e}", icon="🚨")
        st.code(traceback.format_exc())
        return None