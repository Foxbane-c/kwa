#!/usr/bin/env python3
"""PreToolUse Bash, dans l'agent kwa-reviewer seulement — n'autorise que les commandes qui lisent.

Un relecteur qui peut écrire finit par corriger au lieu de relire. Sous Claude Code, ses outils d'écriture sont
retirés ; ce hook ferme la porte du shell. Liste blanche : une commande inconnue est refusée, avec sa raison.
Les commandes de vérification de la politique (verify.commands) restent permises : la relecture doit les lancer.
Sous Codex, c'est le bac à sable en lecture seule de l'agent qui fait ce travail.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kwa import decide, guarded, load_payload, load_policy, segments  # noqa: E402

READ = {"ls", "cat", "head", "tail", "wc", "grep", "rg", "egrep", "fgrep", "awk", "sort", "uniq", "cut", "diff",
        "stat", "file", "tree", "jq", "echo", "printf", "pwd", "which", "type", "basename", "dirname", "realpath",
        "true", "test", "[", "cd", "nl", "column", "less", "more", "comm", "tr", "date"}
GIT_READ = {"diff", "log", "show", "status", "blame", "ls-files", "ls-tree", "grep", "rev-parse", "merge-base",
            "shortlog", "describe", "cat-file", "rev-list", "whatchanged", "name-rev", "for-each-ref"}
GH_READ = {("pr", "view"), ("pr", "diff"), ("pr", "list"), ("pr", "checks"), ("issue", "view"), ("issue", "list"),
           ("run", "view"), ("run", "list"), ("repo", "view")}
WRITE_RE = re.compile(r"(^|[^<>&0-9])>>?|\btee\b")


def allowed(words: list[str], verify: list[list[str]]) -> str:
    """Raison du refus, ou chaîne vide si la commande ne fait que lire."""
    if not words:
        return ""
    cmd = os.path.basename(words[0])
    if any(words[:len(v)] == v for v in verify if v):
        return ""
    if cmd == "git":
        sub = next((w for w in words[1:] if not w.startswith("-")), "")
        if sub == "branch" and not ({"-d", "-D", "--delete", "-m", "-M", "--move", "-c", "-C", "--copy"} & set(words)):
            return ""
        return "" if sub in GIT_READ else f"git {sub} n'est pas une lecture"
    if cmd == "gh":
        pair = tuple(w for w in words[1:3])
        return "" if pair in GH_READ else f"gh {' '.join(pair)} n'est pas une lecture"
    if cmd == "find":
        bad = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprintf", "-fls"} & set(words)
        return f"find {' '.join(sorted(bad))} peut modifier" if bad else ""
    if cmd == "sed":
        return "sed -i modifie le fichier" if any(w.startswith("-i") or w == "--in-place" for w in words[1:]) else ""
    if cmd in READ:
        return ""
    return f"{cmd} n'est pas dans la liste des commandes de lecture"


def main() -> None:
    d = load_payload()
    command = str((d.get("tool_input") or {}).get("command") or "")
    if WRITE_RE.search(re.sub(r"2>&1|>&2|2>/dev/null|>/dev/null", "", command)):
        decide("deny", "relecteur en lecture seule : pas de redirection vers un fichier")
    verify = [c.split() for c in (load_policy(d).get("verify") or {}).get("commands", []) if isinstance(c, str)]
    for words in segments(command):
        reason = allowed(words, verify)
        if reason:
            decide("deny", f"relecteur en lecture seule : {reason}. Rapporter le besoin au lieu de modifier.")


if __name__ == "__main__":
    guarded(main)
