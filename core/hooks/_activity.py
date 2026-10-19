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
        # une seule écriture d'une ligne courte en ajout : deux écrivains ne mêlent pas leurs lignes
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


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
