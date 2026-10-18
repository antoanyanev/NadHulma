#!/usr/bin/env python3
"""
Over the Hill Field Tracker - local server.

Serves the tracker from this folder and saves your progress to progress.json
(next to this script), so it survives clearing the browser and works in any browser.

    python3 tracker_server.py            # then open http://localhost:8000
    python3 tracker_server.py 8123       # use another port

Only listens on this computer (127.0.0.1). Stop it with Ctrl+C.
"""
import json, os, sys, shutil, tempfile, datetime
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
PROGRESS = os.path.join(HERE, "progress.json")
MAX_BODY = 2 * 1024 * 1024


def read_progress():
    try:
        with open(PROGRESS, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("ids"), list):
            return data
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"! progress.json could not be read ({e}); starting empty. The file was left untouched.")
    return {"v": 1, "ids": []}


def write_progress(ids):
    data = {"v": 1, "updated": datetime.datetime.now().isoformat(timespec="seconds"), "count": len(ids), "ids": ids}
    if os.path.exists(PROGRESS):
        shutil.copyfile(PROGRESS, PROGRESS + ".bak")
    fd, tmp = tempfile.mkstemp(dir=HERE, prefix=".progress-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, PROGRESS)


class Handler(SimpleHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/progress":
            return self._json(200, read_progress())
        if self.path.split("?")[0] in ("/progress.json", "/progress.json.bak"):
            return self._json(404, {"error": "not found"})
        return super().do_GET()

    def do_PUT(self):
        if self.path.split("?")[0] != "/api/progress":
            return self._json(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return self._json(400, {"error": "bad size"})
        try:
            body = json.loads(self.rfile.read(n))
            ids = body["ids"]
            if not isinstance(ids, list) or not all(isinstance(i, str) and len(i) < 100 for i in ids):
                raise ValueError("ids must be a list of strings")
        except Exception as e:
            return self._json(400, {"error": str(e)})
        write_progress(sorted(set(ids)))
        print(f"  saved {len(set(ids))} entries to progress.json")
        return self._json(200, {"ok": True})

    def log_message(self, fmt, *args):
        if "/api/" not in (args[0] if args else ""):
            return  # keep the console quiet apart from saves


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    srv = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=HERE))
    print(f"Tracker running at http://localhost:{port}  (progress file: {PROGRESS})")
    print("Press Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
