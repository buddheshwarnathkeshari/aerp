import urllib.request
import urllib.parse
import json

def test():
    # 1. Register
    reg_data = json.dumps({
        "email": "uuid_test2@example.com",
        "password": "SecurePassword123!",
        "first_name": "UUID",
        "last_name": "Test"
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8000/api/v1/auth/register",
        data=reg_data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print("Register:", json.loads(resp.read()))
    except urllib.error.HTTPError as e:
        print("Register Error:", e.code, e.read().decode())

    # 2. Login
    login_data = urllib.parse.urlencode({
        "username": "uuid_test2@example.com",
        "password": "SecurePassword123!"
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8000/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    refresh_token = None
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            print("Login:", json.dumps(data, indent=2))
            refresh_token = data.get("refresh_token")
    except urllib.error.HTTPError as e:
        print("Login Error:", e.code, e.read().decode())

    if not refresh_token:
        return

    # 3. Refresh
    refresh_data = json.dumps({
        "refresh_token": refresh_token
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8000/api/v1/auth/refresh",
        data=refresh_data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print("Refresh:", json.dumps(json.loads(resp.read()), indent=2))
    except urllib.error.HTTPError as e:
        print("Refresh Error:", e.code, e.read().decode())

if __name__ == "__main__":
    test()
