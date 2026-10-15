# Presenter script: explaining process trees with Process Tree Explorer

**Length:** about 12 minutes, plus 3 minutes of live demo if you run the Docker version.
**Audience:** students who know what a program is but haven't studied process management.
**Setup:** open the app full screen. Keep the *Kernel event log* visible; you'll point at it often. Press `?` anytime to view keyboard shortcuts (`1`/`2`/`3` to switch views, `D` for dark mode, `R` to reset, `T` for tour). Fonts are bundled locally so the demo works completely offline without network access.

Stage directions are in *[brackets]*. Lines in quotes are what you say. Adapt the wording, but keep the order: each section builds on the one before.

---

## 0. Opening hook (30 s)

*[Server boot scenario is loaded. Don't click anything yet.]*

> "Every program running on your laptop right now has a parent. Your browser, your terminal, even the clock in the corner. Today we'll look at that family tree, and at the two ways it goes wrong: **zombies**, which are children nobody cleaned up after, and **orphans**, whose parent died first."

---

## 1. Reading the tree (2 min) — *Server boot*

*[Click the `systemd` card, PID 1.]*

> "This is PID 1. The kernel starts exactly one user-space program when the machine boots, and on Ubuntu that's systemd. Everything else descends from it."

*[Point at the second root, `kthreadd`, PID 2.]*

> "There's a second root: kthreadd. It parents the kernel's own worker threads, which is why `ps` shows their names in square brackets. Both roots report PPID 0, which is the kernel itself."

*[Point at a badge.]*

> "Each card has three things. The coloured letter is the state you'd see in the STAT column of `ps`: **S** sleeping, **R** running, **I** idle kernel thread. Then the name, then the PID and the user."

*[Switch to the **ps -ef** tab, then the **pstree** tab, then back to **Graph**.]*

> "It's the same data three ways. `ps -ef` is the flat table you'd get in a terminal; the PPID column is the only thing that encodes the tree. `pstree` draws the tree in text. The graph is the same thing, with the lines made visible."

---

## 2. Lineage (1 min)

*[Click `htop`, PID 2399.]*

> "Who started htop? Follow the blue line back. htop's parent is bash. bash's parent is an `sshd` process for my terminal session, whose parent is a privileged `sshd`, whose parent is the main `sshd` listener, whose parent is systemd."

*[Point at the breadcrumbs in the inspector.]*

> "The inspector shows the same chain. This is how you trace where a mystery process came from on a real server: `ps -o ppid= -p <pid>`, repeat until you hit 1."

---

## 3. fork(), exit(), wait() (2 min)

*[With `bash` (2261) selected, type `sleep 30` in the fork box and press **fork()**.]*

> "When you type a command, bash does two system calls. `fork()` makes a copy of bash with a new PID — watch it appear. Then `execve()` swaps the copy's program for `sleep`. The child's PPID is bash."

*[Point at the FORK line in the event log.]*

*[Select the new `sleep` card and press **exit(0)**. Pause; let the class watch.]*

> "Did you see it turn purple for a moment? When a process exits, the kernel frees its memory but keeps a tiny record: its PID and exit status. That's a **zombie**. The kernel sends the parent a SIGCHLD signal, the parent calls `wait()`, reads the status, and only then does the entry disappear."

*[Point at the EXIT then REAP lines in the log.]*

> "Every process is briefly a zombie. That's normal. It only becomes a problem when the parent never calls `wait()`."

---

## 4. Zombies (3 min) — *Zombies*

*[Click the **Zombies** chip. Select `python3` (3301).]*

> "Here's a buggy server. It forks a handler for each request but never calls `wait()`. Three handlers finished and they're stuck: state **Z**, and `ps` labels them `<defunct>`."

*[Switch to **ps -ef** briefly to show `[python3] <defunct>`, then back.]*

> "They use no CPU and no memory. So why care? Each one holds a PID. PIDs are a finite resource; leak enough and `fork()` starts failing for everyone on the machine."

*[Select a zombie, e.g. 3302, and press **kill -9**. Point at the toast and the log.]*

> "The obvious fix doesn't work. You can't kill a zombie. It's already dead; there's nothing left to receive the signal."

> "There are two real fixes."

*[Select `python3` (3301) and press **wait()**.]*

> "Fix one: the parent calls `wait()`. In real code that means a SIGCHLD handler or calling `waitpid()` in your loop. The zombies are gone."

*[Press **Reset scenario**. Select `python3` (3301) again and press **kill -9**.]*

> "Fix two: kill the parent. Watch the amber dashed lines. The zombies and the live handler are orphaned, the kernel hands them to PID 1, and systemd reaps the zombies at once. The live handler keeps running under its new parent."

---

## 5. Orphans and subreapers (2 min) — *Orphans*

*[Click the **Orphans** chip. Point at the two cards that already have amber edges.]*

> "An orphan is a process whose parent exited first. These two were already adopted: a `sleep` whose shell was closed, and a web server started with `nohup` from an SSH session that's since ended."

*[Select `backup.sh` (2701) and press **kill -9**.]*

> "The backup script crashes. Are rsync and gzip killed too? No. They keep running. But notice where they went: not to PID 1, but to `systemd --user`."

*[Select `systemd --user` (1980); point at the *subreaper* pill and the checkbox.]*

> "That's because it registered as a **child subreaper** with `prctl(PR_SET_CHILD_SUBREAPER)`. The kernel gives an orphan to the nearest living ancestor that's a subreaper, and only falls back to PID 1 if there isn't one. Untick the box, reset, and try again to see the difference."

---

## 6. Containers (1.5 min) — *Containers*

*[Click **Containers**. Point at the two `containerd-shim` cards.]*

> "Each container has its own PID namespace. Inside it, the first process thinks it is PID 1 — see the 'ns 1' on the card — and it inherits init's job of reaping orphans."

*[Select `curl` (4655), the zombie in container B.]*

> "Container B runs python directly as PID 1. Python doesn't reap children it didn't ask for, so this curl is stuck as a zombie forever. Container A runs tini as PID 1, which reaps everything. That's why `docker run --init` exists."

*[Optional: kill `node` (4452) in container A — its workers go to `docker-init`, not to the host's systemd. Then kill `docker-init` — every process in that container disappears.]*

> "And if a container's PID 1 dies, the kernel kills every process in that namespace. That's how a container stops."

---

## 7. Supervisors (30 s) — *Web stack*

*[Click **Web stack**. kill -9 an nginx worker.]*

> "Last pattern. nginx's master gets SIGCHLD, reaps the dead worker and forks a replacement with a new PID. systemd restarting services and Kubernetes restarting pods are the same idea, one level up."

---

## 8. Live demo (3 min, Docker only)

*[Run `docker run --rm -p 8080:8080 process-tree-explorer`, open http://localhost:8080 and click the green **Live** chip.]*

> "Everything so far was a simulation. This tab reads the container's real `/proc` every two seconds."

*[Click **Spawn zombies**.]*

> "That started a real program, `leaky-parent`, which forked three children that exited immediately. Real zombies, state Z."

*[Optional: in another terminal, `docker exec -it <container> ps -ef` to show `<defunct>`.]*

*[Select `leaky-parent`, press **SIGUSR1 → wait()**.]*

> "Its SIGUSR1 handler calls `waitpid()`. The zombies are reaped."

*[Click **Spawn orphan**. Wait about 3 seconds.]*

> "`doomed-parent` forks a child and exits after three seconds. Watch the child's parent change to PID 1, which in this container is tini."

---

## 9. Wrap-up (30 s)

> "Three things to remember.
> One: every process has a parent, and you can trace it back to PID 1.
> Two: a zombie is a finished child its parent hasn't `wait()`ed for. You can't kill it; fix the parent or kill the parent.
> Three: an orphan is a live child whose parent died. It keeps running and is adopted by the nearest subreaper or by PID 1, which must reap it. In containers, make sure PID 1 is something that does."

---

### Likely questions

- **Is a zombie the same as a hung process?** No. A hung process is alive and stuck (often state D or S). A zombie has finished executing.
- **Is an orphan a problem?** Usually not; daemons are often deliberately orphaned. It only matters if the new parent doesn't reap, as in container B.
- **How do I find zombies on a real machine?** `ps -eo pid,ppid,stat,cmd | awk '$3 ~ /Z/'`, then look at the PPID to find the parent that needs fixing.
- **Why can't you kill PID 1?** The kernel ignores signals to init that it hasn't installed handlers for; if init ever exits, the kernel panics.
