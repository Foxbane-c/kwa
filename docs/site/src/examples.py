"""Les fichiers d'exemple du site : une seule source pour la page « Les briques » et le parcours 2.

Formats relus dans la documentation de Claude Code le 2026-10-14. Les tests contrôlent ces exemples : JSON valide,
en-têtes complets, variable DSN pour dbhub, et le hook Python est exécuté pour de bon.
"""
from __future__ import annotations

import json


def _j(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


AGENTS_MD = """# AGENTS.md

Application web (Next.js, pnpm). Répondre en français.

## Vérifier avant de dire « fait »
- `npx tsc --noEmit` puis `pnpm test` : citer le résultat.
- `pnpm lint` signale à tort les fichiers générés : lancer `pnpm lint src`.

## Pièges
- Le serveur de développement écoute sur le port 4000, fixé dans `.env.example`.
- Après un changement de schéma : `pnpm db:migrate:create <nom>` puis `pnpm db:migrate`.

## Interdit
- Pas de commit sur main : une branche par sujet, une PR par branche."""

AGENTS_BAD = """# AGENTS.md

Tu es un expert senior. Écris du code propre, performant et maintenable.
Fais attention à la sécurité. Teste bien ton code. Sois prudent."""

CLAUDE_MD = "@AGENTS.md"

RULE_MD = """---
paths:
  - "src/**/*.tsx"
---

# Composants React

- Tester avec Testing Library, jamais avec Enzyme.
- Un composant par fichier, nommé comme le fichier.
- Pas de style en ligne : les classes du design system."""

SKILL_MD = """---
name: release-notes
description: Rédiger les notes de version à partir des PR fusionnées. À utiliser quand l'utilisateur demande « les notes de version », « le changelog » ou « qu'est-ce qui part en prod ».
---

# Notes de version

1. Lister les PR fusionnées depuis la dernière étiquette :
   `gh pr list --state merged --search "merged:>=<date>"`.
2. Les classer : nouveautés, corrections, technique.
3. Une ligne par PR, au présent, sans jargon interne.
4. Suivre le gabarit de `modele.md` (dans ce dossier)."""

SKILL_ANNEX = """## Version <x.y.z> (<date>)

### Nouveautés
- …

### Corrections
- …"""

AGENT_MD = """---
name: security-reviewer
description: Relit un diff sous l'angle de la sécurité (entrées non validées, secrets, droits). À utiliser avant une PR qui touche l'authentification, les paiements ou les données personnelles.
tools: Read, Grep, Glob
model: sonnet
---

Tu relis un changement sans le modifier. Pour chaque constat : le fichier et la
ligne, ce qui peut arriver, comment le reproduire, la gravité. Si rien ne pose
problème, dis-le en une phrase : n'invente pas de constat."""

HOOK_SETTINGS = {
    "hooks": {
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/no-commit-on-main.py"}]}
        ],
        "PostToolUse": [
            {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "npx tsx \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/format.ts"}]}
        ],
    }
}

HOOK_PY = """#!/usr/bin/env python3
\"\"\"PreToolUse : refuser git commit sur main. Un filet contre l'erreur, pas une barrière.\"\"\"
import json
import re
import subprocess
import sys

COMMIT = re.compile(r"\\bgit(\\s+-[cC]\\s+\\S+)*\\s+commit\\b")  # git commit, git -C dir commit, git -c x=y commit


def refuse(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


try:
    event = json.load(sys.stdin)  # ce que l'agent s'apprête à faire
    command = event.get("tool_input", {}).get("command", "")
    parts = re.split(r"&&|\\|\\||;|\\|", command)  # cd app && git commit : chaque morceau compte
    if not any(COMMIT.search(p) for p in parts):
        sys.exit(0)  # sans sortie : la décision suit son cours normal
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=event.get("cwd"),
                            capture_output=True, text=True, check=True).stdout.strip()
except Exception as error:  # un garde qui plante doit refuser, pas laisser passer
    refuse(f"Garde en erreur ({error}) : vérifier le hook avant de committer.")
if branch == "main":
    refuse("Pas de commit sur main : créer une branche de travail.")"""

HOOK_TS = """// PostToolUse : formater le fichier que l'agent vient d'écrire.
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const event = JSON.parse(readFileSync(0, "utf8"));
const file: string | undefined = event.tool_input?.file_path;
if (file && /\\.(ts|tsx|css)$/.test(file)) {
  execFileSync("npx", ["--no-install", "prettier", "--write", file], { stdio: "ignore" });
}"""

MCP_JSON = {
    "mcpServers": {
        "context7": {"type": "http", "url": "https://mcp.context7.com/mcp", "headers": {"Authorization": "Bearer ${CONTEXT7_API_KEY}"}},
        "base": {"type": "stdio", "command": "npx", "args": ["-y", "@bytebase/dbhub"], "env": {"DSN": "${DB_URL}"}},
    }
}

PERMISSIONS_JSON = {
    "permissions": {
        "allow": ["Bash(pnpm test *)", "Bash(git status)"],
        "ask": ["Bash(git push *)"],
        "deny": ["Read(.env)", "Read(secrets/**)", "Bash(rm -rf *)", "mcp__playwright__browser_run_code_unsafe"],
    }
}

SANDBOX_JSON = {
    "sandbox": {
        "enabled": True,
        "allowUnsandboxedCommands": False,
        "network": {"allowedDomains": ["registry.npmjs.org"]},
        "filesystem": {"allowWrite": ["/tmp/build"]},
    }
}

PLUGIN_TREE = """mon-plugin/
├── .claude-plugin/
│   └── plugin.json          le manifeste : nom, version, où sont les hooks
├── skills/
│   └── release-notes/SKILL.md
├── agents/
│   └── security-reviewer.md
├── hooks/hooks.json         les hooks, au format du bloc hooks de settings.json
└── .mcp.json                facultatif : les serveurs MCP"""

PLUGIN_JSON = {"name": "mon-plugin", "version": "0.1.0", "description": "Les skills, agents et garde-fous de l'équipe."}

POLICY_JSON = {
    "kwa": 1,
    "modules": ["core", "craft", "issue-flow"],
    "bash": {"deny": [{"id": "deploy-prod", "reason": "La production part par la PR, pas par ce script.", "all": ["npm run deploy:prod"]}]},
    "verify": {"commands": ["pnpm typecheck", "pnpm test"]},
}

PROJECT_TREE = """mon-projet/
├── AGENTS.md                      instructions, lues à chaque session
├── CLAUDE.md                      @AGENTS.md (un pointeur)
├── .mcp.json                      serveurs MCP du projet
└── .claude/
    ├── settings.json              permissions et hooks (partagés)
    ├── settings.local.json        vos réglages à vous (hors git)
    ├── rules/                     règles par sujet
    │   └── composants.md
    ├── skills/                    procédures
    │   └── release-notes/
    │       ├── SKILL.md
    │       └── modele.md          annexe, lue au besoin
    ├── agents/                    sous-agents
    │   └── security-reviewer.md
    ├── hooks/                     scripts des hooks
    │   ├── no-commit-on-main.py
    │   └── format.ts
    └── kwa.policy.json            avec Kwa : la politique du projet

~/.claude/                         les mêmes dossiers, pour tous vos projets
├── CLAUDE.md   ├── rules/   ├── skills/   ├── agents/   └── settings.json"""
