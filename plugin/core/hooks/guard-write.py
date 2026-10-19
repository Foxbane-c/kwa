#!/usr/bin/env python3
"""PreToolUse Edit|Write|MultiEdit|NotebookEdit (Claude Code) et apply_patch (Codex) :
  - refuse un secret en clair dans un fichier ;
  - refuse d'écrire un fichier de secrets réel (.env…) : modifier .env.example à la place ;
  - applique write.deny (globs + raison) et write.no_code_on_main (dossiers de code interdits sur main) de la politique ;
  - demande validation avant de toucher à la configuration des gardes eux-mêmes."""
from __future__ import annotations

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kwa import decide, edits, glob_match, guarded, is_secret_path, load_payload, load_policy, project_dir, relative, skill  # noqa: E402

KEYS = [
    ("clé Anthropic", r"sk-ant-[A-Za-z0-9_-]{20,}"),
    ("clé OpenAI", r"\bsk-(proj-)?[A-Za-z0-9_-]{32,}"),
    ("clé Stripe live", r"\b[sr]k_live_[A-Za-z0-9]{16,}"),
    ("clé AWS", r"\bAKIA[0-9A-Z]{16}\b"),
    ("jeton GitHub", r"\b(ghp|gho|ghs|ghu)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}"),
    ("jeton Slack", r"\bxox[abprs]-[A-Za-z0-9-]{20,}"),
    ("clé Scaleway", r"\bSCW[A-Z0-9]{16,}\b"),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("URL de base avec mot de passe", r"\b(postgres(ql)?|mysql|mongodb(\+srv)?|redis|amqp)://[^\s:/@]+:[^\s@/]{3,}@"),
    ("clé privée", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
ALLOW_MARK = "kwa:allow-secret"
PROTECTED = (".claude/settings.json", ".claude/settings.local.json", ".claude/kwa/", ".claude/hooks/", ".codex/hooks.json",
             ".codex/rules/")


def branch_of(path: str) -> str:
    """Branche du checkout qui contient le fichier (le fichier ou ses dossiers peuvent être nouveaux)."""
    folder = os.path.dirname(path)
    while folder and not os.path.isdir(folder) and os.path.dirname(folder) != folder:
        folder = os.path.dirname(folder)
    try:
        return subprocess.run(["git", "-C", folder, "symbolic-ref", "--short", "-q", "HEAD"],
                              capture_output=True, encoding="utf-8", errors="replace", timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def check_path(path: str, d: dict, policy: dict) -> None:
    wr = policy.get("write", {})
    rel = relative(os.path.realpath(path), project_dir(d))
    if is_secret_path(path):
        decide("deny", "Fichier de secrets : modifier le .env.example et laisser le mainteneur reporter la valeur réelle.")
    for rule in wr.get("deny", []):
        if glob_match(rel, rule["glob"]):
            decide("deny", rule["reason"])
    if any(rel.startswith(p) for p in wr.get("no_code_on_main", [])) \
            and branch_of(os.path.realpath(path)) in ({"main", "master"} | set(policy.get("protected_branches", []))):
        decide("deny", f"Pas de code sur main : ouvrir d'abord l'issue et sa branche ({skill('start-dev')}), "
                       "puis travailler dans le worktree créé.")
    if any(rel == p or rel.startswith(p) for p in PROTECTED):
        decide("ask", f"modification de {rel} : c'est la configuration des garde-fous, confirmer")


def check_text(text: str, path: str) -> None:
    for line in (text or "").splitlines():
        if ALLOW_MARK in line:
            continue
        for name, rx in KEYS:
            if re.search(rx, line):
                decide("deny", f"{name} en clair dans {os.path.basename(path) or 'le contenu'} : "
                               "utiliser une variable d'environnement (valeur jamais affichée)")


def main() -> None:
    d = load_payload()
    touched = edits(d)
    policy = load_policy(d) if any(p for p, _, _ in touched) else {}
    for path, text, _kind in touched:
        if path:
            check_path(path, d, policy)
    for path, text, _kind in touched:
        check_text(text, path)


if __name__ == "__main__":
    guarded(main)
