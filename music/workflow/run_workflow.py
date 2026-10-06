"""Submit an API-format ComfyUI workflow and wait for it.

usage: run_workflow.py <api_workflow.json> [timeout_seconds]
"""
import json
import sys
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:8188"


def post(path, payload):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def get(path):
    with urllib.request.urlopen(API + path, timeout=60) as r:
        return json.load(r)


def main():
    api_file = sys.argv[1]
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 1800.0
    prompt = json.load(open(api_file, encoding="utf-8"))

    try:
        res = post("/prompt", {"prompt": prompt, "client_id": "dsh-music-gen"})
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print("VALIDATION FAILED", e.code)
        try:
            err = json.loads(body)
            print("  error:", err.get("error"))
            for nid, ne in (err.get("node_errors") or {}).items():
                print("  node", nid, ne.get("class_type"), "->", ne.get("errors"))
        except Exception:
            print(body[:4000])
        return 2

    pid = res["prompt_id"]
    print("prompt_id", pid, "queue", res.get("number"))
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(5)
        hist = get("/history/" + pid)
        if pid not in hist:
            continue
        entry = hist[pid]
        st = entry["status"]
        print("status:", st["status_str"], "in %.0fs" % (time.time() - t0))
        for m in st.get("messages", []):
            if m[0] == "execution_error":
                print("  ERROR node", m[1].get("node_id"), m[1].get("node_type"))
                print("  ", (m[1].get("exception_message") or "").strip()[:600])
        if st["status_str"] == "success":
            for nid, out in (entry.get("outputs") or {}).items():
                if "text" in out or "saved" in out:
                    print("--- node", nid, "---")
                    for s in out.get("saved", []):
                        print("  saved:", s)
                    for t in out.get("text", []):
                        print(t)
                if out.get("audio"):
                    print("  audio:", out["audio"])
        return 0 if st["status_str"] == "success" else 1
    print("TIMEOUT after", timeout, "s")
    return 3


if __name__ == "__main__":
    sys.exit(main())
