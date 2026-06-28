import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

CREDENTIALS_FILE = "credentials/aerp-integration-95f342c0a1ea.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

# USER INSTRUCTIONS: Paste the ID of your "AERP" folder here.
# You can find it in the URL when you open the folder in Drive:
# https://drive.google.com/drive/folders/<THIS_IS_THE_FOLDER_ID>
FOLDER_ID = "1TCSe7zhDqDca5yme-kNUdL26ZFXLoGFV"

def accept_ownership():
    if not FOLDER_ID:
        print("Please set the FOLDER_ID at the top of the script first!")
        return

    print("Authenticating Service Account...")
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)

    print(f"Fetching permissions for folder: {FOLDER_ID}")
    try:
        # Get all permissions for this folder
        permissions = drive_service.permissions().list(fileId=FOLDER_ID, fields="permissions(id, emailAddress, role, pendingOwner)").execute()
        
        service_account_permission_id = None
        for perm in permissions.get('permissions', []):
            if perm.get('emailAddress') == creds.service_account_email:
                service_account_permission_id = perm.get('id')
                print(f"Found Service Account permission ID: {service_account_permission_id}")
                break
        
        if not service_account_permission_id:
            print("Could not find the Service Account in the permissions list for this folder.")
            return
            
        print("Attempting to accept ownership via API...")
        
        # To accept an ownership transfer, the pending owner updates their own permission role to 'owner'
        drive_service.permissions().update(
            fileId=FOLDER_ID,
            permissionId=service_account_permission_id,
            transferOwnership=True,
            body={'role': 'owner'}
        ).execute()
        
        print("SUCCESS! Ownership was transferred.")
        
    except Exception as e:
        print(f"\nAPI Error: {e}")
        print("\nNote: If you get a '403 Forbidden' or 'Bad Request' error here, it means Google Drive successfully blocked the transfer because you cannot transfer ownership between a @gmail.com account and a @gserviceaccount.com account.")

if __name__ == "__main__":
    accept_ownership()
