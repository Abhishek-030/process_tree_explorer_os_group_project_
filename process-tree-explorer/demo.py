#!/usr/bin/env python3
"""Real process-tree demos for the Live tab (Linux only).

  python3 demo.py zombie   leaky-parent forks 3 children that exit at once and
                           are never reaped (state Z), plus one busy-child.
                           Send it SIGUSR1 and it finally calls waitpid().
  python3 demo.py orphan   doomed-parent forks orphan-child, then exits after
                           3 s. The child is reparented to PID 1 (or the
                           nearest child subreaper).
  python3 demo.py tree     demo-root -> 2 x demo-branch -> 2 x demo-leaf,
                           a well-behaved tree where every parent waits.

Each process renames itself with prctl(PR_SET_NAME) so it is easy to spot in
ps, pstree and the web app. Everything exits on its own within 10 minutes.
"""
import ctypes
import os
import signal
import sys
import time

if sys.platform == "win32":
    print("Error: demo.py requires Linux / POSIX process semantics (fork, prctl).", file=sys.stderr)
    print("To run the live demos on Windows, build and run the Docker container:", file=sys.stderr)
    print("  docker build -t process-tree-explorer .", file=sys.stderr)
    print("  docker run --rm -p 8080:8080 process-tree-explorer", file=sys.stderr)
    sys.exit(1)

LIFETIME = 600
PR_SET_NAME = 15
_libc = ctypes.CDLL(None, use_errno=True)


def set_name(name):
    try:
        _libc.prctl(PR_SET_NAME, name.encode()[:15], 0, 0, 0)
    except Exception:
        pass


def child(name, seconds):
    """fork(); in the child, rename, sleep, exit. Returns the child PID in the parent."""
    pid = os.fork()
    if pid == 0:
        set_name(name)
        time.sleep(seconds)
        os._exit(0)
    return pid


def reap_all(*_):
    while True:
        try:
            pid, _status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            return


def zombie():
    set_name("leaky-parent")
    signal.signal(signal.SIGUSR1, reap_all)  # opt-in reaping on demand
    for i in range(3):
        child("zombie-child", 0.5 + i * 0.4)  # exits quickly, never reaped
    child("busy-child", LIFETIME)
    deadline = time.time() + LIFETIME
    while time.time() < deadline:  # note: never calls wait()
        time.sleep(1)


def orphan():
    set_name("doomed-parent")
    child("orphan-child", LIFETIME)
    time.sleep(3)  # long enough to see the parent/child pair in the Live tab
    os._exit(0)    # parent dies first -> child is orphaned and adopted


def tree():
    set_name("demo-root")
    for _ in range(2):
        if os.fork() == 0:
            set_name("demo-branch")
            for _ in range(2):
                child("demo-leaf", LIFETIME)
            reap_until_empty()
            os._exit(0)
    reap_until_empty()


def reap_until_empty():
    while True:
        try:
            os.wait()
        except ChildProcessError:
            return


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    if kind not in ("zombie", "orphan", "tree"):
        sys.exit("usage: demo.py zombie|orphan|tree")
    os.setpgid(0, 0)  # own process group, so orphans are detectable later
    {"zombie": zombie, "orphan": orphan, "tree": tree}[kind]()
