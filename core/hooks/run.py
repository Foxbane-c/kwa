#!/usr/bin/env python3
"""Point d'entrée des hooks livrés par le plugin Kwa (Claude Code) et par `kwa hook` (Codex) : `run.py <hook>`.

Un plugin est actif dans tous les projets de la machine. Ce lanceur ne passe la main au hook que si le projet a
adopté Kwa (une politique `.claude/kwa.policy.json`, dans le dossier ou dans le dépôt principal pour un worktree)
et que le module du hook y est activé (`modules` de la politique). Un projet encore installé par copie
(`.claude/kwa/state.json`) garde ses propres hooks : le plugin s'efface pour ne pas tout lancer deux fois.
"""
from __future__ import annotations

import io
import json
import os
import runpy
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _kwa  # noqa: E402, F401  règle les flux en UTF-8 avant la lecture de la charge

HOOK_MODULE = {
    "guard-secrets": "core", "guard-git": "core", "guard-delete": "core", "guard-write": "core", "guard-policy": "core",
    "skills-router": "core", "readonly-bash": "craft",  # sous plugin, le routeur porte aussi les règles communes
    "memory-context": "memory", "memory-nudge": "memory", "journal-compact": "memory", "journal-end": "memory",
    "signal-prompt": "memory", "activity-log": "memory",
    "guard-github": "issue-flow",
    "format-after-edit": "verify", "verify-stop": "verify",
}
DEFAULT_MODULES = ["core", "craft", "memory", "issue-flow"]  # politique sans champ « modules »
REVIEWER = {"kwa:reviewer", "kwa-reviewer"}  # nom de l'agent sous plugin, puis en copie


def policy_path(root: str) -> str:
    """La politique du dossier, sinon celle du dépôt principal (un worktree créé avant son commit n'en a pas)."""
    own = os.path.join(root, ".claude", "kwa.policy.json")
    if os.path.isfile(own):
        return own
    if not os.path.isfile(os.path.join(root, ".git")):  # pas un worktree : rien à chercher ailleurs
        return ""
    r = subprocess.run(["git", "-C", root, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                       capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode == 0 and r.stdout.strip():
        main = os.path.join(os.path.dirname(r.stdout.strip()), ".claude", "kwa.policy.json")
        if os.path.isfile(main):
            return main
    return ""


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in HOOK_MODULE:
        print(f"kwa : hook inconnu {sys.argv[1:]}", file=sys.stderr)
        return 0
    name = sys.argv[1]
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        payload = {}
    root = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("KWA_PROJECT_DIR")
                            or payload.get("cwd") or os.getcwd())
    if any(os.path.isfile(os.path.join(root, ".claude", d, "state.json")) for d in ("kwa", "kata")):
        return 0
    path = policy_path(root)
    if not path:
        return 0
    try:
        with open(path, encoding="utf-8") as f:
            policy = json.load(f)
    except (OSError, ValueError):
        policy = {}
    modules = policy.get("modules") if isinstance(policy, dict) else None
    if HOOK_MODULE[name] not in (modules or DEFAULT_MODULES):
        return 0
    if name == "readonly-bash" and payload.get("agent_type") not in REVIEWER:
        return 0
    os.environ["KWA_RUNTIME"] = "plugin"
    os.environ.setdefault("KWA_PROJECT_DIR", root)
    if path != os.path.join(root, ".claude", "kwa.policy.json"):
        os.environ["KWA_POLICY"] = path
    sys.stdin = io.StringIO(raw)
    sys.argv = [os.path.join(HERE, f"{name}.py")]
    runpy.run_path(sys.argv[0], run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main())
