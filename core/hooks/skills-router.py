#!/usr/bin/env python3
"""SessionStart (startup|clear|compact) — rappelle à l'agent quand invoquer quelle skill Kwa.

La table vient de .claude/kwa/router.md ; seules les lignes dont la skill est réellement installée sont gardées
(.claude/skills/kwa-*). Court et calibré : une demande conversationnelle n'appelle aucune skill.
Sous plugin, la table et les règles communes viennent du plugin, filtrées par les modules de la politique : un
plugin ne pose pas de fichier de règles dans le projet, elles arrivent donc ici.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kwa import is_codex, load_payload, load_policy, project_dir, skill  # noqa: E402

PACK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def plugin_context(payload: dict) -> str:
    """Table de routage et règles communes des modules actifs, avec les noms de skills du plugin (/kwa:commit)."""
    with open(os.path.join(PACK, "manifest.json"), encoding="utf-8") as f:
        man = json.load(f)["modules"]
    modules = load_policy(payload).get("modules") or ["core", "craft", "memory", "issue-flow"]
    owner, rules = {}, []
    for m in modules:
        for src, spec in man.get(m, {}).get("files", {}).items():
            got = re.match(r"\.claude/skills/kwa-([a-z-]+)", spec["dest"])
            if got:
                owner[got.group(1)] = m
            if spec["dest"].startswith(".claude/rules/"):
                rules.append(src)
    kept = []
    name = re.compile(r"/kwa[-:]([a-z-]+)")
    with open(os.path.join(PACK, "core", "templates", "skills-router.md"), encoding="utf-8") as f:
        for line in f.read().splitlines():
            got = name.search(line)
            if got and line.startswith("|") and got.group(1) not in owner:
                continue
            kept.append(name.sub(lambda x: skill(x.group(1)), line))
    if not any(name.search(x) for x in kept if x.startswith("|")):
        kept = []  # aucune skill de méthode active : pas de table de routage, seulement les règles
    for src in rules:
        with open(os.path.join(PACK, src), encoding="utf-8") as f:
            kept += ["", name.sub(lambda x: skill(x.group(1)), f.read().strip())]
    return "\n".join(kept)


def main() -> int:
    payload = load_payload()
    root = project_dir(payload)
    if os.environ.get("KWA_RUNTIME") == "plugin":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": plugin_context(payload)}},
                         ensure_ascii=False))
        return 0
    try:
        text = open(os.path.join(root, ".claude", "kwa", "router.md"), encoding="utf-8").read()
    except OSError:
        return 0
    kept = []
    for line in text.splitlines():
        m = re.search(r"/(kwa-[a-z-]+)", line)
        if m and line.startswith("|") and not os.path.isdir(os.path.join(root, ".claude", "skills", m.group(1))):
            continue
        kept.append(line)
    if not any(re.search(r"/kwa-", x) for x in kept if x.startswith("|")):
        return 0
    if is_codex():  # sous Codex, une skill se mentionne avec $ et il n'y a pas d'outil « Skill »
        kept = [x.replace("/kwa-", "$kwa-") for x in kept]
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(kept)}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
