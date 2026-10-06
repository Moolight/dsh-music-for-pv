"""Fetch a faster-whisper CTranslate2 model with plain urllib.

huggingface_hub's snapshot cache creates temp dirs with tempfile.mkdtemp (0o700)
and probes for symlink support by touching files in them; both fail under the DSH
Windows sandbox. CTranslate2 only needs four files, so download them straight.

usage: fetch_whisper_model.py --repo Systran/faster-whisper-small --dest <dir>
"""
import argparse
import os
import sys
import urllib.request

FILES = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]


def fetch(url, path):
    tmp = path + ".part"
    # The mirror 403s the bare urllib user agent.
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "*/*",
    })
    with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as fh:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
            done += len(chunk)
            if total:
                print("\r  %-16s %5.1f%%  %6.1f/%6.1f MB" %
                      (os.path.basename(path), 100.0 * done / total, done / 1e6, total / 1e6), end="")
    print()
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="Systran/faster-whisper-small")
    ap.add_argument("--dest", required=True)
    ap.add_argument("--base", default="https://hf-mirror.com/%s/resolve/main/",
                    help="resolve base; huggingface.co is unreachable here, hf-mirror.com works")
    args = ap.parse_args()

    os.makedirs(args.dest, exist_ok=True)
    base = args.base % args.repo if "%s" in args.base else args.base.rstrip("/") + "/"
    for name in FILES:
        path = os.path.join(args.dest, name)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            print("  %-16s already present (%.1f MB)" % (name, os.path.getsize(path) / 1e6))
            continue
        print("  downloading", name)
        fetch(base + name, path)
    print("model ready:", args.dest)
    for name in FILES:
        p = os.path.join(args.dest, name)
        print("  %-16s %10.1f MB" % (name, os.path.getsize(p) / 1e6))


if __name__ == "__main__":
    sys.exit(main())
