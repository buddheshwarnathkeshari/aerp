import os
import requests
import base64

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
email = env.get("JIRA_EMAIL")
token = env.get("JIRA_API_TOKEN")

auth_string = f"{email}:{token}"
encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

headers = {
    "Authorization": f"Basic {encoded_auth}",
    "Accept": "application/json"
}

url = f"{server}/rest/api/3/myself"
print(f"URL: {url}")
print(f"Email: {email}")
print(f"Token length: {len(token) if token else 0}")
response = requests.get(url, headers=headers)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
