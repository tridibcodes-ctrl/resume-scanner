"""Quick E2E test — upload resumes and analyze via API."""

import json
import urllib.request
import urllib.parse
import os
import sys
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8000"


def post_json(endpoint, data=None):
    url = f"{BASE}{endpoint}"
    body = json.dumps(data).encode("utf-8") if data else b""
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=body or None, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def upload_file(endpoint, filepath, filename):
    url = f"{BASE}{endpoint}"
    boundary = uuid.uuid4().hex

    with open(filepath, "rb") as f:
        file_content = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
    ).encode("utf-8") + file_content + f"\r\n--{boundary}--\r\n".encode("utf-8")

    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    resumes_dir = r"D:\resume-scanner\sample_data\resumes"
    jd_path = r"D:\resume-scanner\sample_data\job_descriptions\senior_software_engineer.txt"

    # 1. Create session
    session = post_json("/api/session")
    sid = session["session_id"]
    print(f"[OK] Created session: {sid}")

    # 2. Upload resumes
    for fname in sorted(os.listdir(resumes_dir)):
        if fname.endswith(".txt"):
            result = upload_file(f"/api/session/{sid}/resumes", os.path.join(resumes_dir, fname), fname)
            print(f"[OK] Uploaded: {fname}")

    # 3. Submit JD
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()
    post_json(f"/api/session/{sid}/job-description", {"text": jd_text})
    print(f"[OK] Submitted JD")

    # 4. Analyze
    print("[...] Running LLM-powered end-to-end analysis across all candidates...")
    results = post_json(f"/api/session/{sid}/analyze")
    print(f"[OK] Analysis complete! Job: {results.get('job_title', 'N/A')}")
    print(f"     Total candidates: {results['total_candidates']}\n")

    # 5. Print rankings
    print("=" * 60)
    print("CANDIDATE RANKINGS")
    print("=" * 60)
    for i, c in enumerate(results["candidates"], 1):
        m = c["match_analysis"]
        print(f"\n#{i} {c['name'] or 'Unknown'} ({c['filename']}) - {m['classification']}")
        print(f"   Overall: {m['overall_score']}% | Skills: {m['skills_score']}% | Exp: {m['experience_score']}% | Edu: {m['education_score']}% | Projects: {m['project_score']}%")
        print(f"   Matched skills ({len(m['matched_skills'])}): {', '.join(s['candidate_skill'] for s in m['matched_skills'][:6])}")
        print(f"   Missing skills: {', '.join(m['missing_skills'][:5])}")
        print(f"   Strengths: {'; '.join(m['strengths'])}")
        print(f"   Justification: {m['justification']}")

    print("\n" + "=" * 60)
    print("Session ID:", sid)
    print("Open http://localhost:5173/ to see the UI")


if __name__ == "__main__":
    main()
