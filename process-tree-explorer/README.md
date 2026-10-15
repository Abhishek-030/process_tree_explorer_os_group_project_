# Process Tree Explorer

An interactive site that visualises Linux process hierarchies: parent/child relationships, zombies (`<defunct>`), orphans and how they are adopted by PID 1 or a child subreaper.

## What's inside

| File / Folder | Purpose |
|---|---|
| `web/index.html` | The whole interactive app, self-contained with offline fonts. Works directly in any browser. |
| `web/fonts/` | Bundled offline fonts (IBM Plex Sans, JetBrains Mono, Schibsted Grotesk WOFF2 files) so no external network access is needed. |
| `server.py` | Cross-platform HTTP server and JSON API over `/proc`, enabling the **Live** tab when run in Docker or Linux. Works on Windows/macOS/Linux. Python stdlib only. |
| `demo.py` | Creates real zombies, an orphan and a demo process tree for the Live tab (Linux/Docker). |
| `Dockerfile`, `docker-compose.yml` | Container image with `tini` as PID 1 and procps utilities. |
| `PRESENTER_SCRIPT.md` | A complete 12–15 minute presentation talk track with step-by-step cues, demo script, and audience Q&A. |
| `process-tree-explorer.zip` | Standalone packaged archive ready for distribution and submission. |

## Run & Deploy

**Live Site (GitHub Pages):**
You can deploy and access this site directly on GitHub Pages at:
👉 **`https://abhishek-030.github.io/process_tree_explorer_os_group_project_/`**

*(To enable: In your repository, go to **Settings** → **Pages** → under **Build and deployment > Source**, select **GitHub Actions**).*

**With Docker (recommended for full Live mode):**

```bash
docker build -t process-tree-explorer .
docker run --rm -p 8080:8080 process-tree-explorer
# open http://localhost:8080 and click the green "Live" chip
```

or `docker compose up --build`.

**With Python server (any OS - Windows, macOS, Linux):**

```bash
python server.py    # or python3 server.py
# open http://localhost:8080
```
*Note:* If run on Linux or inside Docker, the server connects to `/proc` for the Live tab. On Windows and macOS, the simulated scenarios run with full interactivity.

**Static only (any OS, completely offline):**
Open `web/index.html` directly in any web browser. Everything except the Live tab works with zero server or internet requirements.

## Key Features

- **Six real-world scenarios**:
  1. *Server boot*: systemd (PID 1) and kthreadd (PID 2) kernel task roots.
  2. *Web stack*: nginx master/worker pool, Gunicorn, PostgreSQL worker processes.
  3. *Zombies*: Leaky server with `<defunct>` zombie processes.
  4. *Orphans & subreapers*: Crashing backup script, reparenting to `systemd --user` subreaper.
  5. *Containers*: Docker container with `tini` vs container without init.
  6. *Browser*: Chromium master, zygote, GPU, network, and renderer tabs.
- **Three synchronized views**: Interactive Graph, `pstree -p` text tree, and `ps -ef` process table.
- **Realistic Linux kernel semantics**:
  - `kill -9` on a zombie does nothing (dead process cannot receive signals).
  - Orphans are adopted by nearest child subreaper, container init, or PID 1.
  - Killing host PID 1 is refused by the kernel.
  - Killing a container PID 1 cleanly terminates the entire namespace.
  - Supervised masters (nginx) automatically reap dead workers on `SIGCHLD` and respawn replacements.
- **Offline typography**: Self-hosted WOFF2 fonts bundled in `web/fonts/` (no blocked Google Fonts requests in air-gapped/proxy environments).
- **Dark & Light mode**: Dedicated toggle button with automatic system preference detection and localStorage persistence.
- **Search & filter**: Real-time filtering by PID, name, user, or command (`/` shortcut).
- **Keyboard shortcuts**: Hotkeys for power users and presenters (`1`, `2`, `3`, `T`, `R`, `D`, `F`, `/`, `?`).
- **Interactive guided tour**: 11-step pedagogical walkthrough demonstrating process lifecycle and edge cases.
- **Live mode**: Real-time `/proc` inspection with live demo controls (`zombie`, `orphan`, `tree`).
- **Kernel event log**: Real-time event log with timestamps, tags, and one-click clipboard copy (`Copy log`).

## Try the live demos from a terminal

```bash
docker exec -d <container> python3 demo.py zombie
docker exec <container> ps -ef          # look for <defunct>
docker exec -it <container> pstree -p 1
```

To see what happens without an init, run `docker run --rm -p 8080:8080 --entrypoint python3 process-tree-explorer server.py`: the server becomes PID 1, and orphans that exit stay as zombies under it.
