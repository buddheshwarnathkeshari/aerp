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

print(f"Testing GitHub Token: {token[:15]}...{token[-5:]}")
url = "https://api.github.com/user"
headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

resp = requests.get(url, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")
