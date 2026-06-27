import os
import requests
from requests.auth import HTTPBasicAuth
import json

def load_env():
    env_vars = {}
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip()
                except ValueError:
                    pass
    return env_vars

env = load_env()
server = env.get("JIRA_SERVER")
email = "bnkeshari456@gmail.com"  # Using the corrected email
token = env.get("JIRA_API_TOKEN")

auth = HTTPBasicAuth(email, token)
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

print("Checking project KAN...")
meta_url = f"{server}/rest/api/2/issue/createmeta?projectKeys=KAN"
meta_resp = requests.request("GET", meta_url, headers=headers, auth=auth)
if meta_resp.status_code != 200:
    print(f"Failed to fetch project meta: {meta_resp.text}")
    exit(1)

projects = meta_resp.json().get("projects", [])
if not projects:
    print("Project KAN not found or you don't have permission.")
    exit(1)

issue_type_id = projects[0]["issuetypes"][0]["id"]
issue_type_name = projects[0]["issuetypes"][0]["name"]
print(f"Using Issue Type: {issue_type_name} ({issue_type_id})")

tickets = [
    {
        "summary": "User Auth",
        "description": "Users must be able to register and login. The login endpoint should return a JWT token valid for 24 hours. Passwords must be hashed using Django's default PBKDF2 algorithm. MD5 is strictly prohibited."
    },
    {
        "summary": "Razorpay Payments",
        "description": "Integrate Razorpay. Important: Any webhook we receive from Razorpay MUST have its cryptographic signature verified using our secret key before we mark an order as paid. Also, ensure users can only initiate payments for their own orders."
    },
    {
        "summary": "Product Search",
        "description": "Build a product search endpoint. Performance is critical—use select_related/prefetch_related to avoid N+1 database queries when fetching products and their categories. The search term must be parameterized to prevent SQL injection."
    },
    {
        "summary": "Inventory",
        "description": "When an order is placed, decrement the available quantity. Since we expect high traffic, you MUST use database-level row locking (select_for_update) to prevent race conditions where two users buy the last item at the exact same millisecond."
    },
    {
        "summary": "Order Dashboard",
        "description": "Create an order history endpoint for users, and a dashboard for admins. Ensure strict permission scoping so users cannot read other people's orders."
    },
    {
        "summary": "Coupons",
        "description": "Create an endpoint to apply discount codes. Business rule: A discount can NEVER make the order total drop below zero (minimum price is $0). Also, wrap the coupon usage count increment in an atomic database transaction."
    }
]

created_keys = []

for i, ticket in enumerate(tickets):
    payload = json.dumps({
        "fields": {
            "project": {"key": "KAN"},
            "summary": f"[PR {i+1}] {ticket['summary']}",
            "description": ticket["description"],
            "issuetype": {"id": issue_type_id}
        }
    })
    
    url = f"{server}/rest/api/2/issue"
    response = requests.request("POST", url, data=payload, headers=headers, auth=auth)
    
    if response.status_code == 201:
        key = response.json().get("key")
        print(f"Created Jira Ticket: {key}")
        created_keys.append(key)
    else:
        print(f"Failed to create ticket: {response.text}")

print(f"All created keys: {created_keys}")

with open("jira_mapping.json", "w") as f:
    json.dump(created_keys, f)
