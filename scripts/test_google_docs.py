import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

FOLDER_ID = "1TCSe7zhDqDca5yme-kNUdL26ZFXLoGFV"
CREDENTIALS_FILE = "credentials/aerp-integration-95f342c0a1ea.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

def test_drive_upload():
    print("Authenticating...")
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)

    print("Attempting to upload a .txt file to the folder...")
    file_metadata = {
        'name': 'AERP_Test.txt',
        'parents': [FOLDER_ID]
    }
    media = MediaIoBaseUpload(io.BytesIO(b"Hello World"), mimetype='text/plain', resumable=True)
    
    try:
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"Success! File created with ID: {file.get('id')}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_drive_upload()
