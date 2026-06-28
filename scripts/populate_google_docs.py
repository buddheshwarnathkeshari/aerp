import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

CREDENTIALS_FILE = "credentials/aerp-integration-95f342c0a1ea.json"
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

# USER INSTRUCTIONS: Paste the IDs of your 6 blank Google Docs here.
# You can find the ID in the URL: https://docs.google.com/document/d/<THIS_IS_THE_ID>/edit
DOC_IDS = [
    "1tMk9wb6P6ghRFOuyn604m-7XTmylOHbNTvQRV5dkHs0", # Doc 1
    "12XNZEJ6cmf9ehBsLNqMIIA8ehuhcIUR4lNCAChN8nUg", # Doc 2
    "12LXyJvyuJPZHJvIO_TT7ugsMHTD2Mowvt-xath0yKQ4", # Doc 3
    "1i-60yFgFXWKT6Vb0E1NyhI_df5cgQmpUb7u2E1gRPKE", # Doc 4
    "1e-Ti1ROSkeVMXcVdZh5Wc6S7cMRr-WQV-eLm587k7Wk", # Doc 5
    "19JvTe5O2bx7vWl4EaXCys5F79RCqzhJ7lcaHgabtC1A"  # Doc 6
]

def populate_docs():
    print("Authenticating with Google APIs...")
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
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

    for i, doc_id in enumerate(DOC_IDS):
        if not doc_id:
            print(f"Skipping Doc {i+1} because ID is empty.")
            continue
            
        item = docs_data[i]
        try:
            # 1. Update the document title
            # Google Docs title is updated via Google Drive API, wait! 
            # It's easier to just append the title to the body.
            
            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': 1,
                        },
                        'text': f"{item['title']}\n\n{item['body']}"
                    }
                }
            ]
            docs_service.documents().batchUpdate(
                documentId=doc_id, body={'requests': requests}).execute()
                
            print(f"Successfully populated: https://docs.google.com/document/d/{doc_id}/edit")
        except Exception as e:
            print(f"Error populating {doc_id}: {e}")

if __name__ == "__main__":
    populate_docs()
