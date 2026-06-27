import os
import requests

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
token = env.get("GITHUB_TOKEN")
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

repo = "buddheshwarnathkeshari/aerp-test-dataset"

# Map PR number to the new Jira Ticket Key we created
mapping = {
    1: "KAN-5",
    2: "KAN-6",
    3: "KAN-7",
    4: "KAN-8",
    5: "KAN-9",
    6: "KAN-10"
}

# Also map to the Google Doc URLs we populated!
doc_mapping = {
    1: "https://docs.google.com/document/d/1tMk9wb6P6ghRFOuyn604m-7XTmylOHbNTvQRV5dkHs0/edit",
    2: "https://docs.google.com/document/d/12XNZEJ6cmf9ehBsLNqMIIA8ehuhcIUR4lNCAChN8nUg/edit",
    3: "https://docs.google.com/document/d/12LXyJvyuJPZHJvIO_TT7ugsMHTD2Mowvt-xath0yKQ4/edit",
    4: "https://docs.google.com/document/d/1i-60yFgFXWKT6Vb0E1NyhI_df5cgQmpUb7u2E1gRPKE/edit",
    5: "https://docs.google.com/document/d/1e-Ti1ROSkeVMXcVdZh5Wc6S7cMRr-WQV-eLm587k7Wk/edit",
    6: "https://docs.google.com/document/d/19JvTe5O2bx7vWl4EaXCys5F79RCqzhJ7lcaHgabtC1A/edit"
}

for pr_number, jira_key in mapping.items():
    print(f"Fetching PR #{pr_number}...")
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to fetch PR {pr_number}: {resp.text}")
        continue
        
    body = resp.json().get("body", "")
    
    # Replace the old SHOP-10x with the new KAN-x
    old_ticket = f"SHOP-10{pr_number}"
    new_body = body.replace(old_ticket, jira_key)
    
    # Add Google Doc link to the body if it's not already there
    doc_link = f"\n\n## PRD / Spec\n[Google Doc Spec]({doc_mapping[pr_number]})"
    if "Google Doc Spec" not in new_body:
        new_body += doc_link
    
    print(f"Updating PR #{pr_number} to link to {jira_key} and Google Docs...")
    patch_resp = requests.patch(url, headers=headers, json={"body": new_body})
    if patch_resp.status_code == 200:
        print(f"Successfully updated PR #{pr_number}")
    else:
        print(f"Failed to update PR #{pr_number}: {patch_resp.text}")

print("All PRs updated successfully!")
