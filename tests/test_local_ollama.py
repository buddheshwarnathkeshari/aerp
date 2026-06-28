import requests
import time
import sys

API_URL = "http://localhost:8000/reviews"

payload = {
    "pr_url": "https://github.com/fake/repo/pull/1",
    "github_pr_metadata": {
        "title": "Add local Ollama support",
        "description": "This PR integrates local Ollama LLMs into the project to run privately.",
        "author": "dev1"
    },
    "jira_ticket": {
        "ticket_id": "AERP-101",
        "title": "Enable local models",
        "status": "In Progress",
        "priority": "High",
        "description": "Users need to run AERP without internet access.",
        "acceptance_criteria": ["Support local LLM execution", "Provider agnostic architecture"]
    },
    "architecture_doc_url": "https://docs.google.com/document/d/fake/edit",
    "changed_files": [
        "backend/utils/llm_factory.py",
        "docker-compose.yml"
    ]
}

def main():
    print("🚀 Submitting review to API...")
    try:
        response = requests.post(f"{API_URL}/start", json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to submit review: {e}")
        sys.exit(1)

    data = response.json()
    review_id = data.get("review_id")
    print(f"✅ Review started! ID: {review_id}")
    print("⏳ Waiting for Celery worker & Ollama to finish... (This may take a few minutes)")
    
    start_time = time.time()
    while True:
        try:
            status_resp = requests.get(f"{API_URL}/{review_id}", timeout=5)
            status_data = status_resp.json()
            status = status_data.get("status")
            
            elapsed = int(time.time() - start_time)
            print(f"[{elapsed}s] Current Status: {status}")
            
            if status in ["completed", "failed", "paused_for_review"]:
                print(f"\n🎉 Workflow finished with status: {status}")
                if status_data.get("agent_findings"):
                    print(f"Found {len(status_data['agent_findings'])} agent findings.")
                break
                
            time.sleep(10)
        except requests.RequestException as e:
            print(f"⚠️ Error polling status: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
