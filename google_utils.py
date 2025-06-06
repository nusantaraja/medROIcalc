#!/usr/bin/env python3
# Utility functions for Google Sheets and Google Drive integration

import streamlit as st
import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import io
import traceback # For detailed error logging

# Define the scopes required for Sheets and Drive API
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- Authentication --- 
def get_google_credentials():
    """Authenticates using service account credentials from Streamlit secrets."""
    try:
        # Assuming secrets are stored under [google_credentials] in secrets.toml
        creds_json = st.secrets["google_credentials"]
        creds = service_account.Credentials.from_service_account_info(creds_json, scopes=SCOPES)
        return creds
    except KeyError:
        # This error is handled in the main script, no need to show error here
        return None
    except Exception as e:
        st.error(f"Error loading or parsing Google credentials from secrets: {e}")
        # st.code(traceback.format_exc()) # Optional: Show full traceback
        return None

def get_gspread_client(credentials):
    """Returns an authenticated gspread client."""
    if credentials:
        try:
            return gspread.authorize(credentials)
        except Exception as e:
            st.error(f"Error creating gspread client: {e}")
            # st.code(traceback.format_exc())
            return None
    return None

def get_drive_service(credentials):
    """Returns an authenticated Google Drive API service."""
    if credentials:
        try:
            return build("drive", "v3", credentials=credentials)
        except Exception as e:
            st.error(f"Error creating Google Drive service: {e}")
            # st.code(traceback.format_exc())
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
        worksheet.append_row(data_row, value_input_option="USER_ENTERED")
        # Keep success message minimal, main script handles overall status
        # st.success(f"Data successfully appended to Google Sheet: {sheet_name}")
        return True
    except gspread.exceptions.APIError as e:
        st.error(f"Google Sheets API Error appending data: {e}. Check Sheet ID ", icon="🚨")
        st.info(f"Details: Sheet ID=\"{sheet_id}\", Sheet Name=\"{sheet_name}\". Ensure the Service Account has Editor permissions.")
        # st.code(traceback.format_exc())
        return False
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet ", icon="🚨")
        return False
    except Exception as e:
        st.error(f"Unexpected error appending data to Google Sheet: {e}", icon="🚨")
        # st.code(traceback.format_exc())
        return False

# --- Google Drive Operations --- 
def upload_pdf_to_drive(drive_service, pdf_content, filename, folder_id):
    """Uploads PDF content to a specific Google Drive folder and returns the shareable link."""
    if not drive_service:
        st.error("Google Drive service not available for uploading PDF.")
        return None
    try:
        # Create a file metadata
        file_metadata = {
            "name": filename,
            "parents": [folder_id], # Ensure folder_id is correct and service account has access
            "mimeType": "application/pdf"
        }

        # Create a BytesIO object from the PDF content
        pdf_bytes_io = io.BytesIO(pdf_content)

        # Create a MediaFileUpload object
        media = MediaFileUpload(pdf_bytes_io, mimetype="application/pdf", resumable=True)

        # Upload the file
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink" # Request the webViewLink
        ).execute()

        file_id = file.get("id")
        web_view_link = file.get("webViewLink")

        # Optional: Make the file publicly viewable (requires specific Drive permissions)
        # try:
        #     drive_service.permissions().create(
        #         fileId=file_id,
        #         body={\"type\": \"anyone\", \"role\": \"reader\"}
        #     ).execute()
        # except Exception as perm_error:
        #     st.warning(f"Could not set public permissions for the uploaded PDF: {perm_error}")

        # Keep success message minimal
        # st.success(f"PDF ", icon="📄")
        return web_view_link

    except Exception as e:
        st.error(f"Error uploading PDF to Google Drive: {e}", icon="🚨")
        st.info(f"Details: Attempted to upload ", icon="ℹ️")
        # st.code(traceback.format_exc())
        return None

