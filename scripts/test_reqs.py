import requests
import json
import time

# --- Configuration ---
BASE_URL = "http://127.0.0.1:7000"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/token/"
BULK_UPLOAD_URL = f"{BASE_URL}/api/v1/resumes/bulk-upload/"

USERNAME = "test"
PASSWORD = "test@123"

# Sample resume paths (as provided by user)
SAMPLE_FILES = [
    r"d:\Projects\Academic Projects\Resume Parse Pro AI\sample_resumes\EPS-Computer-Science.pdf",
    r"d:\Projects\Academic Projects\Resume Parse Pro AI\sample_resumes\LAB-Business-and-Finance.pdf"
]

# Requirements to test
REQUIREMENTS = {
    "required_skills": ["Python", "Computer Science"],  # Target the CS resume
    "min_years_experience": 0,
    "use_llm_validation": True # Test LLM validation
}

def login():
    print(f"Logging in as {USERNAME}...")
    try:
        resp = requests.post(LOGIN_URL, data={"username": USERNAME, "password": PASSWORD}) 
        if resp.status_code != 200:
             resp = requests.post(LOGIN_URL, json={"username": USERNAME, "password": PASSWORD})

        if resp.status_code == 200:
            token = resp.json().get("access")
            print("Login successful! Token acquired.")
            return token
        else:
            print(f"Login failed: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def upload_resumes(token, files, requirements):
    print(f"\nUploading {len(files)} resumes with requirements...")
    headers = {"Authorization": f"Bearer {token}"}
    
    files_to_send = []
    file_handles = []
    for fpath in files:
        try:
            fh = open(fpath, "rb")
            file_handles.append(fh)
            files_to_send.append(("files", (fpath.split("\\")[-1], fh, "application/pdf")))
        except Exception as e:
            print(f"Could not open file {fpath}: {e}")

    if not file_handles:
        print("No files to upload.")
        return

    data = {"requirements": json.dumps(requirements)}
    
    # sync=1 to force waiting for processing (so we can see if it fails or succeeds immediately)
    upload_url = f"{BULK_UPLOAD_URL}?sync=1"  
    print(f"POST {upload_url}")
    
    try:
        # Increased timeout for sync processing 
        resp = requests.post(upload_url, headers=headers, files=files_to_send, data=data, timeout=120)
        print(f"Response Code: {resp.status_code}")
        
        try:
            r = resp.json()
            if r.get("success") or resp.status_code in [200, 201, 202]:
                data = r.get("data", {}) if "data" in r else r
                print("\n--- Summary ---")
                print(f"Total: {data.get('total')}")
                print(f"Successful: {data.get('successful')}")
                print(f"Accepted Count: {data.get('matching')}")
                print(f"Rejected Count: {data.get('rejected_count')}")
                print(f"Error Count: {data.get('error_count')}")
                
                print("\n--- Detailed Results ---")
                for item in data.get("results", []):
                    status = "REJECTED" if item.get("discarded") else "ACCEPTED"
                    if item.get("duplicate"):
                        status += " (Duplicate)"
                    print(f"File: {item.get('filename')} -> {status}")
                    if item.get("discarded"):
                        print(f"  Reasons: {item.get('discard_reasons')}")
                
                print("\n--- Errors ---")
                for err in data.get("errors", []):
                    print(f"File: {err.get('filename')} -> {err.get('error')} ({err.get('error_code')})")
            else:
                print(f"Error: {r.get('error')}")
                print(json.dumps(r, indent=2))
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            print(resp.text)
            
    except Exception as e:
        print(f"Upload failed: {e}")
        
    finally:
        for fh in file_handles:
            fh.close()

if __name__ == "__main__":
    token = login()
    if token:
        upload_resumes(token, SAMPLE_FILES, REQUIREMENTS)
