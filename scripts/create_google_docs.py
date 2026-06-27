import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Folder ID provided by user
FOLDER_ID = "1TCSe7zhDqDca5yme-kNUdL26ZFXLoGFV"

# Path to the JSON key
CREDENTIALS_FILE = "credentials/aerp-integration-95f342c0a1ea.json"

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

def create_docs():
    print("Authenticating with Google APIs...")
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)

    docs_data = [
        {
            "title": "AERP-1: User Auth",
            "body": "Users must be able to register and login. The login endpoint should return a JWT token valid for 24 hours. Passwords must be hashed using Django's default PBKDF2 algorithm. MD5 is strictly prohibited."
        },
        {
            "title": "AERP-2: Razorpay Payments",
            "body": "Integrate Razorpay. Important: Any webhook we receive from Razorpay MUST have its cryptographic signature verified using our secret key before we mark an order as paid. Also, ensure users can only initiate payments for their own orders."
        },
        {
            "title": "AERP-3: Product Search",
            "body": "Build a product search endpoint. Performance is critical—use select_related/prefetch_related to avoid N+1 database queries when fetching products and their categories. The search term must be parameterized to prevent SQL injection."
        },
        {
            "title": "AERP-4: Inventory",
            "body": "When an order is placed, decrement the available quantity. Since we expect high traffic, you MUST use database-level row locking (select_for_update) to prevent race conditions where two users buy the last item at the exact same millisecond."
        },
        {
            "title": "AERP-5: Order Dashboard",
            "body": "Create an order history endpoint for users, and a dashboard for admins. Ensure strict permission scoping so users cannot read other people's orders."
        },
        {
            "title": "AERP-6: Coupons",
            "body": "Create an endpoint to apply discount codes. Business rule: A discount can NEVER make the order total drop below zero (minimum price is $0). Also, wrap the coupon usage count increment in an atomic database transaction."
        }
    ]

    created_urls = []

    for item in docs_data:
        # Create a new Google Doc via Drive API in the specific folder
        file_metadata = {
            'name': item['title'],
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [FOLDER_ID]
        }
        
        try:
            doc = drive_service.files().create(body=file_metadata, fields='id').execute()
            doc_id = doc.get('id')
            
            # Insert text into the document
            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': 1,
                        },
                        'text': item['body']
                    }
                }
            ]
            docs_service.documents().batchUpdate(
                documentId=doc_id, body={'requests': requests}).execute()
                
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            print(f"Created '{item['title']}' at: {doc_url}")
            created_urls.append(doc_url)
        except Exception as e:
            print(f"Error creating '{item['title']}': {e}")

    print("\nSuccessfully created documents:")
    for url in created_urls:
        print(url)

if __name__ == "__main__":
    create_docs()
