#!/usr/bin/env python3
"""Process Tree Explorer server.

Serves the web app and a small JSON API that reads the real process table
from /proc, so the "Live" tab shows actual parent/child relationships,
zombies and orphans inside the container. Standard library only.

  GET  /api/processes            -> every process from /proc
  POST /api/spawn   {kind}       -> start demo.py zombie|orphan|tree
  POST /api/signal  {pid, sig}   -> signal a demo process (KILL/TERM/USR1/STOP/CONT)
  POST /api/cleanup              -> SIGKILL every demo process
"""
import json
import os
import platform
import signal
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

try:
    import pwd
except ImportError:
    pwd = None

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web")
DEMO_NAMES = {"leaky-parent", "zombie-child", "busy-child", "doomed-parent",
              "orphan-child", "demo-root", "demo-branch", "demo-leaf"}
SIGNALS = {
    "KILL": getattr(signal, "SIGKILL", 9),
    "TERM": getattr(signal, "SIGTERM", 15),
    "USR1": getattr(signal, "SIGUSR1", 10),
    "STOP": getattr(signal, "SIGSTOP", 19),
    "CONT": getattr(signal, "SIGCONT", 18),
}


def read_proc(pid):
    """Parse one /proc/<pid> entry. Returns None if the process vanished."""
    try:
        if not os.path.exists(f"/proc/{pid}/stat"):
            return None
        with open(f"/proc/{pid}/stat", "rb") as f:
            stat = f.read().decode(errors="replace")
        # comm is wrapped in parentheses and may itself contain spaces or ')'
        left, right = stat.index("("), stat.rindex(")")
        comm = stat[left + 1:right]
        fields = stat[right + 2:].split()
        state, ppid, pgrp, sid = fields[0], int(fields[1]), int(fields[2]), int(fields[3])
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmd = f.read().replace(b"\0", b" ").decode(errors="replace").strip()
        uid = 0
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("Uid:"):
                    uid = int(line.split()[1])
                    break
        user = str(uid)
        if pwd:
            try:
                user = pwd.getpwuid(uid).pw_name
            except (KeyError, Exception):
                pass
    except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError, IndexError, OSError):
        return None
    return {"pid": pid, "ppid": ppid, "pgrp": pgrp, "sid": sid, "comm": comm,
            "cmd": cmd or f"[{comm}]", "state": state, "user": user}


def read_procs():
    if not os.path.isdir("/proc"):
        return []
    procs = [p for p in (read_proc(int(d)) for d in os.listdir("/proc") if d.isdigit()) if p]
    pids = {p["pid"] for p in procs}
    for p in procs:
        # Heuristic for "adopted orphan": its parent is PID 1, yet the process
        # group it inherited belongs to a leader that no longer exists.
        p["adopted"] = p["ppid"] == 1 and p["pgrp"] != p["pid"] and p["pgrp"] not in pids
    return sorted(procs, key=lambda p: p["pid"])


def comm_of(pid):
    try:
        with open(f"/proc/{pid}/comm") as f:
            return f.read().strip()
    except (OSError, FileNotFoundError):
        return None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB, **kwargs)

    def log_message(self, fmt, *args):  # keep container logs quiet
        pass

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/processes"):
            hostname = platform.node() or "localhost"
            has_proc = os.path.isdir("/proc")
            procs = read_procs()
            return self.send_json(200, {
                "host": hostname,
                "server_pid": os.getpid(),
                "processes": procs,
                "has_proc": has_proc
            })
        return super().do_GET()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"error": "Body must be JSON."})

        if not os.path.isdir("/proc") or sys.platform == "win32":
            return self.send_json(400, {
                "error": "Live demos require Linux /proc (run in Docker: docker run --rm -p 8080:8080 process-tree-explorer)"
            })

        if self.path == "/api/spawn":
            kind = body.get("kind")
            if kind not in ("zombie", "orphan", "tree"):
                return self.send_json(400, {"error": "kind must be zombie, orphan or tree"})
            proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "demo.py"), kind])
            # Reap our own direct child so the server never leaks a zombie itself.
            threading.Thread(target=proc.wait, daemon=True).start()
            return self.send_json(200, {"msg": f"server.py spawned demo '{kind}' as PID {proc.pid}"})

        if self.path == "/api/signal":
            try:
                pid, sig = int(body.get("pid")), body.get("sig")
            except (TypeError, ValueError):
                return self.send_json(400, {"error": "pid must be a number"})
            if sig not in SIGNALS:
                return self.send_json(400, {"error": "Unsupported signal"})
            if comm_of(pid) not in DEMO_NAMES:
                return self.send_json(403, {"error": "Only processes started by the demos can be signalled."})
            try:
                os.kill(pid, SIGNALS[sig])
            except ProcessLookupError:
                return self.send_json(404, {"error": "That process has already gone."})
            return self.send_json(200, {"msg": f"sent SIG{sig} to PID {pid}"})

        if self.path == "/api/cleanup":
            n = 0
            for p in read_procs():
                if p["comm"] in DEMO_NAMES and p["state"] != "Z":
                    try:
                        os.kill(p["pid"], signal.SIGKILL)
                        n += 1
                    except ProcessLookupError:
                        pass
            return self.send_json(200, {"msg": f"SIGKILL sent to {n} demo process(es)"})

        return self.send_json(404, {"error": "Unknown endpoint"})


def main():
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    ppid = os.getppid() if hasattr(os, "getppid") else 0
    print(f"Process Tree Explorer on http://localhost:{port}  (PID {os.getpid()}, parent {ppid})", flush=True)
    if not os.path.isdir("/proc"):
        print("Note: Running without Linux /proc. Web app is fully functional with 6 simulated scenarios.")
        print("To enable Live mode with real container processes, run via Docker.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
