import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

CREDENTIALS_FILE = "credentials/aerp-integration-95f342c0a1ea.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

# The AERP Folder ID that the Service Account now owns
FOLDER_ID = "1TCSe7zhDqDca5yme-kNUdL26ZFXLoGFV"

def test_create_doc():
    print("Authenticating Service Account...")
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)

    print(f"Attempting to create a new Google Doc inside folder: {FOLDER_ID}")
    
    file_metadata = {
        'name': 'AERP Auto-Created Test Doc',
        'mimeType': 'application/vnd.google-apps.document',
        'parents': [FOLDER_ID]
    }
    
    try:
        file = drive_service.files().create(body=file_metadata, fields='id').execute()
        print(f"\nSUCCESS! File created with ID: {file.get('id')}")
        print("The Service Account has successfully created a file inside the folder!")
    except Exception as e:
        print(f"\nFAILED! Error creating file: {e}")

if __name__ == "__main__":
    test_create_doc()
