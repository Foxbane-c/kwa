"""Journal d'activité (module memory) : ce qui se passe dans une session, une ligne JSON par événement.

Un fichier par session dans `.claude/kwa/local/activity/` du dépôt principal : des sessions en parallèle, y compris
dans des worktrees, n'écrivent jamais dans le même fichier. Rien de versionné, rien qui quitte la machine, aucun
contenu de fichier ni de prompt : un nom d'outil, une brique, un chemin ou une commande tronqués et nettoyés.
Bibliothèque standard uniquement. Désactivé avec le journal (KWA_JOURNAL=0).
"""
from __future__ import annotations

import json
import os
import re
import time

from _journal import enabled, local_dir, scrub
from _kwa import relative, under

SESSION_BYTES = 1024 * 1024        # plafond d'un fichier de session (environ 5 000 lignes)
TOTAL_BYTES = 20 * 1024 * 1024     # plafond du dossier : au-delà, les plus anciens partent
KEEP_DAYS = 30                     # durée de garde par défaut (memory.activity_days)
TARGET_CHARS = 120                 # longueur gardée d'un chemin ou d'une commande
# Toujours écrits, même au-delà du plafond : ce sont les étapes, pas le détail.
STEPS = {"session", "skill", "agent", "agent-end", "deny", "turn"}
_UNSAFE = re.compile(r"[^A-Za-z0-9_-]")


def activity_dir(root: str, create: bool = True) -> str:
    d = os.path.join(local_dir(root, create), "activity")
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def activity_days(policy: dict | None) -> int:
    try:
        return max(1, int(((policy or {}).get("memory") or {}).get("activity_days", KEEP_DAYS)))
    except (TypeError, ValueError):
        return KEEP_DAYS


def session_file(root: str, session: str, create: bool = True) -> str:
    """Le fichier de la session : celui qui existe déjà (une session qui passe minuit garde le sien), sinon un neuf
    daté du jour."""
    sid = _UNSAFE.sub("", session or "")[:64] or "sans-session"
    d = activity_dir(root, create)
    try:
        for name in os.listdir(d):
            if name.endswith(f"-{sid}.jsonl"):
                return os.path.join(d, name)
    except OSError:
        pass
    return os.path.join(d, f"{time.strftime('%Y-%m-%d')}-{sid}.jsonl")


def _short(value: object) -> str:
    text = scrub(" ".join(str(value).split()))
    return text if len(text) <= TARGET_CHARS else text[:TARGET_CHARS - 1] + "…"


def record(root: str, session: str, kind: str, agent: str = "claude", **fields: object) -> None:
    """Ajoute un événement au journal de la session. Jamais bloquant : une erreur d'écriture est ignorée.

    Au-delà du plafond d'un fichier, seules les étapes (STEPS) sont encore écrites ; les autres événements sont
    seulement comptés, par brique, dans `<fichier>.counts.json`."""
    if not enabled():
        return
    try:
        path = session_file(root, session)
        rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "ts": round(time.time(), 3), "kind": kind, "agent": agent}
        rec.update({k: _short(v) for k, v in fields.items() if v not in (None, "")})
        line = json.dumps(rec, ensure_ascii=False) + "\n"
        if kind not in STEPS and os.path.exists(path) and os.path.getsize(path) >= SESSION_BYTES:
            _count(path, str(fields.get("brick") or "autre"))
            return
        _append(path, line)
    except OSError:
        pass


def _append(path: str, line: str) -> None:
    """Une ligne ajoutée d'un seul appel : sous POSIX, O_APPEND garantit que deux écrivains ne mêlent pas leurs lignes.
    Sous Windows, l'ajout est un déplacement puis une écriture, non atomique : un verrou sur le premier octet du
    fichier le remplace (msvcrt attend jusqu'à 10 s, puis l'erreur est ignorée par record)."""
    data = line.encode("utf-8")
    with open(path, "ab") as f:
        if os.name != "nt":
            f.write(data)
            return
        import msvcrt

        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        try:
            f.write(data)
            f.flush()
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


# Ce que fait un appel d'outil, en une brique : la même lecture que le mod kwa-activity. Les noms d'outils de Codex
# (shell, apply_patch) et de Copilot (convertis en noms Claude quand ses hooks sont au format Claude) sont compris.
READ_TOOLS = {"Read", "NotebookRead", "Grep", "Glob", "LS", "WebFetch", "WebSearch", "view", "glob", "grep", "web_fetch"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "apply_patch", "create", "edit"}
SHELL_TOOLS = {"Bash", "shell", "bash", "powershell"}
TEST = re.compile(r"\b(test|tests|pytest|unittest|jest|vitest|mocha|tsc|lint|eslint|typecheck|go test|cargo (test|check)"
                  r"|mvn (test|verify)|gradle (test|check)|dotnet (build|test))\b")
SHIP = re.compile(r"\b(git (commit|push|merge|tag)|gh pr (create|merge))\b")


def classify(tool: str, tool_input: dict, verify: list[str] | None = None, root: str = "") -> tuple[str, str]:
    """(brique, cible) d'un appel d'outil ; brique vide pour une commande qui ne relève d'aucune étape."""
    path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path") or "")
    if root and path != root and under(path, root):
        path = relative(path, root)
    if tool in READ_TOOLS:
        return "cadrer", path or str(tool_input.get("pattern") or tool_input.get("url") or tool_input.get("query") or "")
    if tool in WRITE_TOOLS:
        if tool == "apply_patch":
            m = re.search(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", str(tool_input.get("input") or tool_input.get("patch") or ""), re.M)
            path = m.group(1).strip() if m else path
        return "faire", path
    if tool in SHELL_TOOLS:
        cmd = tool_input.get("command") or ""
        cmd = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        if any(v and v in cmd for v in (verify or [])) or TEST.search(cmd):
            return "prouver", cmd
        if SHIP.search(cmd):
            return "livrer", cmd
        return "", cmd
    return "", ""


def _count(path: str, brick: str) -> None:
    counts_path = path + ".counts.json"
    try:
        with open(counts_path, encoding="utf-8") as f:
            counts = json.load(f)
    except (OSError, ValueError):
        counts = {}
    counts[brick] = int(counts.get(brick, 0)) + 1
    tmp = counts_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(counts, f)
    os.replace(tmp, counts_path)


def read_session(root: str, session: str) -> list[dict]:
    """Les événements d'une session, dans l'ordre ; une ligne illisible est ignorée."""
    out: list[dict] = []
    try:
        with open(session_file(root, session, create=False), encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def prune(root: str, policy: dict | None = None, now: float | None = None) -> int:
    """Supprime les fichiers de session plus vieux que la durée de garde, puis les plus anciens tant que le dossier
    dépasse son plafond. Renvoie le nombre de fichiers supprimés."""
    d = activity_dir(root, create=False)
    try:
        names = os.listdir(d)
    except OSError:
        return 0
    now = time.time() if now is None else now
    cutoff = now - activity_days(policy) * 86400
    files = []
    for name in names:
        p = os.path.join(d, name)
        if name.endswith(".jsonl") and os.path.isfile(p):
            files.append((os.path.getmtime(p), p))
    removed = 0
    files.sort()
    kept = []
    for mtime, p in files:
        if mtime < cutoff:
            removed += _remove(p)
        else:
            kept.append((mtime, p))
    total = sum(_size(p) for _, p in kept)
    for _, p in kept:
        if total <= TOTAL_BYTES:
            break
        total -= _size(p)
        removed += _remove(p)
    return removed


def _size(p: str) -> int:
    try:
        return os.path.getsize(p) + (os.path.getsize(p + ".counts.json") if os.path.exists(p + ".counts.json") else 0)
    except OSError:
        return 0


def _remove(p: str) -> int:
    try:
        os.unlink(p)
        if os.path.exists(p + ".counts.json"):
            os.unlink(p + ".counts.json")
        return 1
    except OSError:
        return 0
