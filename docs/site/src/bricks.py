"""Page « Les briques » : chaque mécanisme d'un agent de code (instructions, règle, skill, sous-agent, hook, serveur MCP,
permission, plugin, politique Kwa) sur une même fiche : pourquoi, quand, qui le déclenche, où il vit, ce qu'il garantit,
un fichier d'exemple complet et son pendant réel dans Kwa.

Les formats suivent la documentation de Claude Code (hooks, skills, sous-agents, MCP, permissions, plugins), relue le
2026-10-14. Les exemples sont contrôlés par les tests : JSON valide, en-têtes complets, et le hook Python d'exemple
est exécuté pour de bon (il doit refuser un commit sur main).
"""
from __future__ import annotations

import html
import json

import pictos
from parcours import code

REPO = "https://github.com/nesyouyou/kwa/blob/main/"
DOC = "https://code.claude.com/docs/en/"

AGENTS_MD = """# AGENTS.md

Application web (Next.js, pnpm). Répondre en français.

## Vérifier avant de dire « fait »
- `pnpm typecheck` puis `pnpm test` : citer le résultat.

## Pièges
- Après un changement de schéma : `pnpm db:migrate:create <nom>`.

## Interdit
- Pas de commit sur main : une branche par sujet."""

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
        "deny": ["Read(.env)", "Bash(rm -rf *)"],
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


def _j(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


# Une brique : (id, pictogramme, nom, phrase, nature, pourquoi, quand, pas quand, qui la déclenche, où, coût,
#               [(chemin, contenu)], (fichier réel dans Kwa, légende))
BRICKS = [
    ("instructions", "doc", "Instructions (AGENTS.md)", "Ce que l'agent doit savoir sur le projet, à chaque session.", "suggéré",
     "Une session repart de zéro. Ce fichier transmet ce que l'agent ne peut pas deviner en lisant le code : les commandes de vérification, les pièges, les interdits.",
     "Un fait valable partout et tout le temps : comment lancer les tests, le port du serveur, la convention de branche.",
     "Une consigne qui ne concerne qu'une partie du code (une règle), une procédure longue (une skill), une interdiction qui doit tenir (un hook).",
     "Personne : il est chargé au démarrage de chaque session.",
     "<code>AGENTS.md</code> à la racine ; <code>CLAUDE.md</code> pour Claude Code, qui peut n'être qu'un pointeur.",
     "Toujours dans la fenêtre : restez court.",
     [("AGENTS.md", AGENTS_MD), ("CLAUDE.md", CLAUDE_MD)],
     ("core/templates/agents-block.md", "le bloc que Kwa gère dans AGENTS.md")),
    ("regle", "list", "Règle (.claude/rules/)", "Une consigne rangée par sujet, chargée quand elle sert.", "suggéré",
     "Quand AGENTS.md grossit, tout y est lu à chaque fois. Une règle isole un sujet ; avec <code>paths</code>, elle n'entre dans le contexte que quand l'agent touche un fichier concerné.",
     "Une convention propre à un dossier ou à un type de fichier : les composants React, les migrations, l'API.",
     "Un fait général (AGENTS.md) ou une étape à exécuter dans l'ordre (une skill).",
     "Personne : chargée au démarrage, ou quand l'agent lit, écrit ou modifie un fichier qui correspond à <code>paths</code> (après une compaction, elle revient au prochain fichier concerné).",
     "<code>.claude/rules/*.md</code> dans le projet, <code>~/.claude/rules/</code> pour vous.",
     "Au démarrage sans <code>paths</code> ; seulement au besoin avec.",
     [(".claude/rules/composants.md", RULE_MD)],
     ("core/rules/git-discipline.md", "une règle commune de Kwa, rappelée au démarrage")),
    ("skill", "sword", "Skill (SKILL.md)", "Une procédure que l'agent suit quand la situation correspond.", "suggéré",
     "Une tâche qui revient se fait toujours de la même façon. La skill l'écrit une fois ; seule sa description reste dans le contexte, le corps n'est lu qu'à l'appel.",
     "Une procédure à étapes, déclenchée par une demande : rédiger des notes de version, livrer une PR, déboguer.",
     "Un fait à connaître en permanence (AGENTS.md) ou une contrainte qui doit tenir même si l'agent l'oublie (un hook).",
     "Le modèle, quand la description correspond à la demande ; ou vous, en tapant <code>/release-notes</code>.",
     "<code>.claude/skills/&lt;nom&gt;/SKILL.md</code>, ses annexes à côté ; <code>~/.claude/skills/</code> pour vous ; ou un plugin.",
     "La description (1 536 caractères au plus) en permanence. Une fois appelée, le corps reste dans la conversation jusqu'à la fin ; après une compaction, les skills récentes sont réattachées (5 000 jetons chacune, 25 000 au total).",
     [(".claude/skills/release-notes/SKILL.md", SKILL_MD), (".claude/skills/release-notes/modele.md", SKILL_ANNEX)],
     ("plugin/skills/tdd/SKILL.md", "/kwa:tdd, le test d'abord")),
    ("sous-agent", "agent", "Sous-agent (.claude/agents/)", "Un second collaborateur, avec sa propre fenêtre de contexte.", "mixte",
     "Lire trente fichiers remplit la fenêtre de l'agent principal. Un sous-agent le fait à part et ne rend qu'un résumé. Il peut aussi avoir moins d'outils : un relecteur qui ne peut pas écrire relit mieux.",
     "Un travail de lecture volumineux, une relecture indépendante, plusieurs tâches en parallèle.",
     "Une petite tâche : le brief et le résumé coûtent plus que de la faire dans la session.",
     "Le modèle, ou une skill qui le lance ; vous, en le demandant (« lance le relecteur »).",
     "<code>.claude/agents/&lt;nom&gt;.md</code> ; <code>~/.claude/agents/</code> pour vous ; ou un plugin.",
     "Sa propre fenêtre, où il relit les fichiers d'instructions ; seul son résumé revient. La description de chaque sous-agent reste dans la fenêtre principale.",
     [(".claude/agents/security-reviewer.md", AGENT_MD)],
     ("plugin/agents/reviewer.md", "kwa:reviewer, le relecteur en lecture seule")),
    ("hook", "hook", "Hook", "Un script que l'outil exécute à un moment précis, sans demander au modèle.", "imposé",
     "Une instruction peut être oubliée. Un hook ne dépend pas du modèle : Claude Code l'exécute, toujours, avant ou après un outil, au démarrage, à la fin d'une réponse. Mais il juge un texte : une commande formulée autrement peut lui échapper. C'est un filet contre l'erreur ; une vraie barrière, c'est le bac à sable ou la protection de branche.",
     "Refuser une action (commit sur main, lecture d'un secret), formater après une écriture, réinjecter du contexte au démarrage.",
     "Une décision qui demande du jugement : un hook lit du texte, il ne comprend pas l'intention.",
     "Claude Code, à l'événement choisi (<code>PreToolUse</code>, <code>PostToolUse</code>, <code>SessionStart</code>, <code>Stop</code>…).",
     "Déclaré dans <code>.claude/settings.json</code> ; le script où vous voulez, souvent <code>.claude/hooks/</code>. Python, TypeScript, bash : n'importe quel langage qui lit l'entrée standard.",
     "Aucun, sauf ce qu'il renvoie à l'agent.",
     [(".claude/settings.json", _j(HOOK_SETTINGS)), (".claude/hooks/no-commit-on-main.py", HOOK_PY), (".claude/hooks/format.ts", HOOK_TS)],
     ("core/hooks/guard-git.py", "guard-git, le garde de git de Kwa")),
    ("mcp", "plug", "Serveur MCP", "Des outils et des données branchés sur l'agent : une doc, un navigateur, une base.", "suggéré",
     "L'agent ne voit que son dépôt. Un serveur MCP lui ajoute des outils, que le modèle découvre et décide d'appeler : chercher dans une doc à jour, piloter un navigateur, lire une base.",
     "Un accès à un service ou à des données hors du dépôt.",
     "Une procédure (une skill) ; un serveur que vous ne connaissez pas : il agit avec vos droits. En session interactive, Claude Code demande avant d'utiliser les serveurs d'un <code>.mcp.json</code> ; en <code>claude -p</code> et dans le SDK, il les charge sans demander.",
     "Le modèle, qui appelle ses outils (<code>mcp__context7__…</code>).",
     "<code>.mcp.json</code> à la racine du projet (partagé) ; <code>claude mcp add</code> l'ajoute pour ce projet et vous seul, <code>--scope user</code> pour tous vos projets.",
     "Les noms des outils ; leurs définitions à la demande.",
     [(".mcp.json", _j(MCP_JSON))],
     ("parcours-contexte.html#etape-7", "parcours 2, étapes 7 et 8 : MCP, Context7, Playwright, Graphify")),
    ("permission", "shield", "Permission", "Ce que l'agent a le droit de faire, décidé hors de son texte.", "imposé",
     "Évite de valider chaque commande à la main, et ferme ce qui ne doit jamais se faire. Claude Code l'applique avant l'outil, quoi qu'en pense le modèle.",
     "Autoriser les commandes sûres et fréquentes, demander avant un push, refuser un fichier de secrets.",
     "Une règle qui dépend du contexte (la branche, le contenu) : un hook la calcule, une permission ne voit que la commande.",
     "Claude Code, avant chaque outil : <code>deny</code>, puis <code>ask</code>, puis <code>allow</code>.",
     "<code>.claude/settings.json</code> (partagé), <code>.claude/settings.local.json</code> (vous seul), <code>~/.claude/settings.json</code>.",
     "Aucun.",
     [(".claude/settings.json", _j(PERMISSIONS_JSON))],
     ("parcours-contexte.html#etape-9", "parcours 2, étape 9 : permissions et réglages")),
    ("sandbox", "lock", "Bac à sable", "Une limite posée par le système d'exploitation autour des commandes shell.", "barrière",
     "Une permission ou un hook lisent le texte d'une commande ; une commande écrite autrement leur échappe. Le bac à sable, lui, contraint le processus lui-même : les fichiers qu'il peut écrire, les sites qu'il peut joindre, quoi que la commande dise.",
     "Laisser l'agent lancer des commandes sans confirmation, sur un projet où une fuite ou une suppression coûterait cher.",
     "Les outils de fichiers (Read, Edit), les serveurs MCP et les hooks : ils tournent hors du bac à sable et suivent les permissions. Et Windows natif : il faut WSL2.",
     "Le système d'exploitation, pendant chaque commande shell de l'agent, et pour les processus qu'elle lance.",
     "<code>/sandbox</code> dans une session, ou <code>sandbox.enabled</code> dans settings.json. Désactivé par défaut.",
     "Aucun.",
     [(".claude/settings.json", _j(SANDBOX_JSON))],
     ("impose.html", "Imposé ou suggéré : où le bac à sable se place")),
    ("plugin", "box", "Plugin", "Un paquet de skills, d'agents, de hooks et de serveurs, installé une fois par machine.", "selon le contenu",
     "Copier les mêmes fichiers dans dix dépôts, c'est dix copies qui divergent. Un plugin les regroupe, se met à jour d'un coup, et le projet ne garde que sa configuration.",
     "Partager une méthode entre plusieurs projets ou plusieurs personnes.",
     "Un réglage propre à un seul projet : il reste dans le dépôt. À savoir : ses skills prennent son préfixe (<code>/mon-plugin:release-notes</code>) ; ses hooks désignent leurs scripts par <code>${CLAUDE_PLUGIN_ROOT}</code>, pas <code>$CLAUDE_PROJECT_DIR</code> ; un <code>CLAUDE.md</code> placé dans un plugin n'est pas lu. <code>claude plugin validate</code> vérifie le tout.",
     "Vous : <code>/plugin install</code> ; le projet peut le proposer à l'équipe dans <code>settings.json</code>.",
     "<span class=\"br-flow\"><span>un dépôt Git, la marketplace</span><span><code>/plugin install</code> sur votre machine</span><span>activé dans le projet par <code>settings.json</code></span></span>",
     "Celui de ce qu'il contient.",
     [("mon-plugin/", PLUGIN_TREE), (".claude-plugin/plugin.json", _j(PLUGIN_JSON))],
     ("plugin/.claude-plugin/plugin.json", "le manifeste du plugin Kwa")),
    ("politique", "settings", "Politique Kwa", "Ce qui change d'un projet à l'autre, lu par les gardes et les skills de Kwa.", "imposé (par les gardes)",
     "Les gardes sont les mêmes partout ; les commandes interdites, les vérifications et les environnements, non. La politique les décrit, sans toucher aux scripts.",
     "Interdire une commande propre au projet, déclarer les vérifications, choisir les modules.",
     "Une règle valable pour tous les projets : elle va dans Kwa lui-même.",
     "Les gardes de Kwa, à chaque outil surveillé ; les skills, quand elles en ont besoin.",
     "<code>.claude/kwa.policy.json</code>, créé par <code>kwa init</code>, puis propriété du projet.",
     "Aucun.",
     [(".claude/kwa.policy.json", _j(POLICY_JSON))],
     ("examples/expo-monorepo.policy.json", "une politique complète d'exemple")),
]

# Ce qu'il faut savoir pour lire chaque fichier d'exemple : (repère dans le fichier, explication)
NOTES = {
    "CLAUDE.md": [("@AGENTS.md", "un import : Claude Code lit AGENTS.md à la place, et Codex lit AGENTS.md directement. Un seul fichier à tenir.")],
    ".claude/rules/composants.md": [
        ("--- … ---", "l'en-tête, en YAML : des paires « clé: valeur » que l'outil lit, le modèle ne les voit pas comme du texte."),
        ("paths", "les fichiers concernés. <code>**</code> veut dire « dans tous les sous-dossiers », <code>*.tsx</code> « tout fichier qui finit par .tsx ». Sans <code>paths</code>, la règle est lue à chaque session, comme AGENTS.md : on la range à part seulement pour garder AGENTS.md court."),
    ],
    ".claude/skills/release-notes/SKILL.md": [
        ("name", "le nom de la commande : <code>/release-notes</code>. Dans un plugin, il prend le préfixe du plugin (<code>/kwa:tdd</code>) ; sous Codex, on tape <code>$</code> au lieu de <code>/</code>."),
        ("description", "la seule partie toujours chargée. Le modèle la compare à votre demande pour décider d'appeler la skill : dites quand l'utiliser, avec les mots que l'on emploie vraiment."),
        ("modele.md", "une annexe : lue seulement si la skill en a besoin, donc gratuite le reste du temps."),
    ],
    ".claude/agents/security-reviewer.md": [
        ("tools", "les seuls outils qu'il aura : ici lire et chercher, pas écrire. C'est l'outil qui l'applique : la partie imposée d'un sous-agent. Le reste du fichier est du texte qu'il suit."),
        ("model", "le modèle qui le fait tourner : <code>sonnet</code>, <code>opus</code>, <code>haiku</code>, ou absent pour garder celui de la session."),
        ("le texte sous l'en-tête", "ses consignes. Il ne voit rien de votre conversation : seulement la tâche que l'agent principal lui donne. Sans Bash, il ne lance pas <code>git diff</code> : le diff lui est fourni dans la demande (le relecteur de Kwa a Bash, en lecture seule, gardé par un hook)."),
    ],
    ".claude/settings.json#hooks": [
        ("PreToolUse, PostToolUse", "l'événement : avant ou après un outil. Il en existe une trentaine (démarrage, fin de réponse…)."),
        ("matcher", "le nom de l'outil visé : <code>Bash</code> (le terminal), <code>Edit|Write</code> (l'un ou l'autre)."),
        ("type: command", "le hook est un programme à lancer ; <code>command</code> est sa ligne de commande."),
        ("$CLAUDE_PROJECT_DIR", "la racine du projet, remplie par Claude Code : le chemin marche quel que soit le dossier courant."),
    ],
    ".claude/hooks/no-commit-on-main.py": [
        ("json.load(sys.stdin)", "Claude Code envoie sur l'entrée standard ce que l'agent s'apprête à faire : l'outil, sa commande, le dossier."),
        ("re.split(…)", "<code>cd app &amp;&amp; git commit</code> est une seule commande pour l'outil : on la découpe, sinon le commit passe."),
        ("sys.exit(0) sans rien afficher", "« pas d'avis » : l'action suit son cours normal (permissions, demande éventuelle)."),
        ("permissionDecision: deny", "le refus. La raison est renvoyée à l'agent, qui la lit et change de cap : ici, il crée une branche."),
        ("except Exception", "un script qui plante sort en code 1, ce qui ne bloque rien : un garde doit attraper ses propres erreurs et refuser."),
        ("ou bien exit 2", "l'autre façon de refuser : écrire la raison sur la sortie d'erreur et sortir avec le code 2. Le JSON permet en plus <code>ask</code> (demander) ou <code>allow</code>."),
    ],
    ".claude/hooks/format.ts": [
        ("readFileSync(0)", "lit l'entrée standard, comme le script Python : n'importe quel langage fait l'affaire."),
        ("npx --no-install", "utilise le prettier du projet sans rien télécharger ; un hook n'apporte pas ses dépendances (ici Node.js, tsx, prettier)."),
        ("le fichier change sous l'agent", "après formatage, la prochaine modification de l'agent peut échouer sur un texte qui n'existe plus : il relit le fichier et recommence."),
    ],
    ".mcp.json": [
        ("type: http", "un service distant, joint par une adresse ; <code>headers</code> porte l'authentification."),
        ("type: stdio", "un programme lancé sur votre machine (<code>npx -y</code> le télécharge puis le lance), qui parle par l'entrée et la sortie standard."),
        ("${CONTEXT7_API_KEY}", "une variable d'environnement : la clé n'est jamais écrite dans le fichier, qui peut donc être versionné."),
        ("DSN", "le nom de variable que ce serveur attend pour la base : chaque serveur documente les siens."),
    ],
    ".claude/settings.json#permissions": [
        ("Bash(pnpm test *)", "la commande <code>pnpm test</code> suivie de n'importe quoi (l'étoile)."),
        ("Read(.env)", "un nom de fichier seul vaut à toute profondeur (comme dans un .gitignore) ; <code>./.env</code> ne viserait que le dossier courant. <code>.env.local</code> demande sa propre ligne."),
        ("Bash(rm -rf *)", "un filet : <code>rm -fr</code> ou <code>/bin/rm</code> passent à côté. Une règle Bash lit le texte de la commande."),
        ("deny, ask, allow", "évaluées dans cet ordre : un refus l'emporte toujours, même sur une autorisation plus précise, et vaut aussi pour chaque morceau d'une commande composée."),
    ],
    ".claude-plugin/plugin.json": [
        ("name", "le préfixe de ses skills et de ses agents : <code>/mon-plugin:release-notes</code>."),
        ("pas de chemin de hooks", "<code>hooks/hooks.json</code> est l'emplacement par défaut ; un champ <code>hooks</code> en ajoute un autre (Kwa s'en sert)."),
    ],
    ".claude/settings.json#sandboxs": [
        ("allowUnsandboxedCommands: false", "sans cela, Claude peut demander à relancer une commande hors du bac à sable quand elle échoue."),
        ("network.allowedDomains", "les seuls sites joignables par le shell ; la liste part vide."),
        ("filesystem.allowWrite", "les dossiers où écrire, en plus du projet."),
    ],
    ".claude/kwa.policy.json": [
        ("bash.deny", "une commande que les gardes de Kwa refusent, avec la raison donnée à l'agent. Le même refus vaut sous Codex."),
        ("verify.commands", "les vérifications que les skills de Kwa lancent avant de dire « fait »."),
    ],
}

# Pièges à connaître, par fiche (dépliés à la demande)
PITFALLS = {
    "hook": """<table class="pc-table"><thead><tr><th>Sortie du script</th><th>Avant l'outil (PreToolUse)</th><th>Après (PostToolUse)</th><th>Fin de réponse (Stop)</th></tr></thead><tbody>
<tr><td>0 sans rien</td><td>pas d'avis</td><td>rien</td><td>l'agent s'arrête</td></tr>
<tr><td>0 et un JSON</td><td>la décision du JSON (deny, ask, allow)</td><td>un retour pour l'agent</td><td>peut demander de continuer</td></tr>
<tr><td>2</td><td>refus, la sortie d'erreur part à l'agent</td><td>trop tard : l'outil a déjà tourné</td><td>l'agent repart travailler</td></tr>
<tr><td>1 ou autre</td><td colspan="3">erreur sans effet : l'action continue</td></tr></tbody></table>
<ul class="pc-list">
<li><strong>Tous les hooks d'un même événement tournent en parallèle</strong>, sans ordre : deux formateurs sur le même fichier se marchent dessus.</li>
<li><strong>Un hook Stop qui refuse toujours fait boucler l'agent</strong> : testez <code>stop_hook_active</code> ; Claude Code rend la main après 8 relances d'affilée.</li>
<li><strong>Un hook peut être déclaré ailleurs</strong> : réglages personnels ou locaux, plugin, en-tête d'une skill ou d'un agent. <code>/hooks</code> les montre tous.</li>
</ul>""",
    "skill": """<ul class="pc-list">
<li>Un champ mal orthographié dans l'en-tête est ignoré sans erreur.</li>
<li>Une skill personnelle (<code>~/.claude/skills/</code>) l'emporte sur une skill du projet qui porte le même nom.</li>
<li><code>disable-model-invocation: true</code> la réserve à vous : utile pour ce qui a des effets (déployer, publier).</li>
</ul>""",
    "mcp": """<ul class="pc-list">
<li>Un même serveur déclaré à plusieurs endroits : la définition locale gagne, puis celle du projet, puis la vôtre, puis celle d'un plugin.</li>
<li>Un dépôt cloné peut apporter un <code>.mcp.json</code> : en <code>claude -p</code> ou en CI, il est chargé sans demander. <code>disabledMcpjsonServers</code> en exclut un.</li>
</ul>""",
    "permission": """<ul class="pc-list">
<li>Un <code>deny</code> de n'importe quel fichier de réglages l'emporte sur un <code>allow</code> d'un autre.</li>
<li>Une règle Bash lit la commande écrite : <code>bash -c '…'</code> ou un chemin complet passent à côté. Pour une vraie limite, le bac à sable.</li>
</ul>""",
}

# Vérifier que la brique est active : (ce que l'on fait, ce que l'on doit voir)
CHECK = {
    "instructions": ("<code>/context</code> dans une session", "AGENTS.md (ou CLAUDE.md) dans la liste des fichiers de mémoire chargés"),
    "regle": ("<code>/context</code>, puis demander à l'agent de modifier un fichier <code>.tsx</code>", "la règle apparaît dans le contexte après la lecture du fichier"),
    "skill": ("<code>/skills</code>, puis taper <code>/release-notes</code>", "la skill dans la liste ; à l'appel, l'agent suit ses étapes"),
    "sous-agent": ("demander « utilise security-reviewer pour relire mon diff »", "l'agent lance le sous-agent, qui travaille à part puis rend son résumé"),
    "hook": ("<code>/hooks</code>, puis demander un commit sur main", "le hook dans la liste ; le commit est refusé avec la raison du script"),
    "mcp": ("<code>/mcp</code>", "le serveur connecté et ses outils"),
    "permission": ("<code>/permissions</code>", "vos règles, rangées par portée (projet, local, personnel)"),
    "sandbox": ("<code>/sandbox</code>, puis demander à l'agent « curl https://example.com »", "le bac à sable actif ; la requête est refusée, le domaine n'étant pas autorisé"),
    "plugin": ("<code>/plugin</code>", "le plugin installé et activé ; ses skills dans <code>/skills</code>"),
    "politique": ("<code>kwa doctor .</code> dans le terminal", "« cible conforme », ou la liste de ce qui manque"),
}

NEEDS = [  # (besoin, brique, pourquoi)
    ("L'agent doit savoir comment lancer les tests", "instructions", "un fait valable à chaque session"),
    ("Les composants React se testent avec Testing Library", "regle", "ne concerne que certains fichiers"),
    ("Rédiger les notes de version de la même façon à chaque fois", "skill", "une procédure, appelée quand on la demande"),
    ("Relire une PR sans que le relecteur puisse modifier le code", "sous-agent", "une fenêtre à part, des outils réduits"),
    ("Ne jamais committer sur main, même si l'agent l'oublie", "hook", "doit tenir sans dépendre du modèle"),
    ("Formater chaque fichier après son écriture", "hook", "automatique, à chaque écriture"),
    ("Lire la doc de la bonne version d'une bibliothèque", "mcp", "un accès à un service hors du dépôt"),
    ("Ne plus valider pnpm test à la main", "permission", "une commande sûre, autorisée d'avance"),
    ("Partager les mêmes skills et gardes entre cinq dépôts", "plugin", "une seule source, mise à jour d'un coup"),
    ("Interdire npm run deploy:prod dans ce projet", "permission", "une ligne deny : Bash(npm run deploy:prod*) ; une politique Kwa seulement s'il faut aussi l'appliquer sous Codex"),
    ("Refuser un curl qui contient à la fois prod et reset", "politique", "une combinaison de motifs (all, any), qu'une règle de permission ne sait pas dire"),
    ("Empêcher le shell de joindre autre chose que le registre npm", "sandbox", "une limite que le système d'exploitation fait respecter, quelle que soit la commande"),
    ("Une procédure que je lance seulement à la main", "skill", "avec disable-model-invocation: true, le modèle ne la déclenche jamais seul"),
    ("Ne pas rendre la main tant que les tests sont rouges", "hook", "un hook Stop ; attention à la boucle, Claude Code s'arrête après 8 relances"),
]


def _lang(path: str) -> str:
    return path.rsplit(".", 1)[-1] if "." in path.rsplit("/", 1)[-1] else "tree"


def notes(path: str, bid: str) -> str:
    items = NOTES.get(f"{path}#{bid}s" if path.endswith("settings.json") else path, [])
    if not items:
        return ""
    lis = "".join(f"<li><code>{html.escape(k)}</code> {v}</li>" for k, v in items)
    return f'<ul class="br-notes" aria-label="À lire dans ce fichier">{lis}</ul>'


def card(b) -> str:
    bid, pic, name, line, nature, why, when, when_not, who, where, cost, files, real = b
    tabs = "".join(f'<button type="button" class="br-tab" role="tab" id="{bid}-t{i}" aria-controls="{bid}-f{i}" aria-selected="{str(i == 0).lower()}" tabindex="{0 if i == 0 else -1}" data-f="{i}">{html.escape(p)}</button>'
                   for i, (p, _c) in enumerate(files))
    panes = "".join(f'<div class="br-file" role="tabpanel" id="{bid}-f{i}" aria-labelledby="{bid}-t{i}" data-f="{i}"{"" if i == 0 else " hidden"}>{code(c)}{notes(p, bid)}</div>' for i, (p, c) in enumerate(files))
    do, see = CHECK[bid]
    pit = f'<details class="br-pit"><summary>Les pièges</summary>{PITFALLS[bid]}</details>' if bid in PITFALLS else ""
    kind = nature.split(" ")[0].split(",")[0]
    return f"""<article class="br-card" id="{bid}">
<header><span class="br-pic">{pictos.svg(pic)}</span><div><h2>{html.escape(name)}</h2><p>{html.escape(line)}</p></div>
<span class="kd-kind kd-kind--{kind}">{html.escape(nature)}</span></header>
<dl class="br-facts">
<div><dt>Pourquoi</dt><dd>{why}</dd></div>
<div><dt>Quand l'utiliser</dt><dd>{when}</dd></div>
<div><dt>Quand ce n'est pas le bon outil</dt><dd>{when_not}</dd></div>
<div><dt>Qui le déclenche</dt><dd>{who}</dd></div>
<div><dt>Où il vit</dt><dd>{where}</dd></div>
<div><dt>Ce qu'il coûte au contexte</dt><dd>{cost}</dd></div>
<div class="br-check"><dt>Vérifier que ça marche</dt><dd>{do} : {see}.</dd></div>
</dl>
{pit}
<div class="br-ex"><div class="br-tabs" role="tablist" aria-label="Fichiers d'exemple">{tabs}</div>{panes}
<p class="br-real">{"Pas à pas" if ".html" in real[0] else "Dans Kwa"} : <a href="{real[0] if ".html" in real[0] else REPO + real[0]}">{html.escape(real[1])}</a></p></div>
</article>"""


def page() -> str:
    names = {b[0]: b[2] for b in BRICKS}
    nav = "".join(f'<a href="#{b[0]}">{pictos.svg(b[1])}{html.escape(b[2].split(" (")[0])}</a>' for b in BRICKS)
    lis = lambda ids: "".join(f'<li><a href="#{i}">{html.escape(names[i].split(" (")[0])}</a></li>' for i in ids)
    guess = "".join(f'<button type="button" class="br-g" data-g="{b[0]}">{html.escape(b[2].split(" (")[0])}</button>' for b in BRICKS)
    needs = "".join(f'<button type="button" class="br-need" aria-pressed="false" data-to="{to}" data-why="{html.escape(why)}">{html.escape(need)}</button>'
                    for need, to, why in NEEDS)
    return f"""<p class="kw-lead">Un agent de code se règle avec une poignée de briques. Elles ne se ressemblent pas : certaines sont du
<strong>texte que le modèle lit</strong> et peut oublier, d'autres sont <strong>exécutées par l'outil</strong> et tiennent quoi qu'il arrive.
Chaque fiche dit pourquoi la brique existe, quand s'en servir, où elle vit, et montre un vrai fichier.</p>
<nav class="br-nav" aria-label="Les briques">{nav}</nav>

<section class="br-split" aria-labelledby="br-split-h"><h2 id="br-split-h" class="br-h">Lu par le modèle, ou exécuté par l'outil</h2>
<div class="br-cols">
<div class="br-col"><b><span class="kd-kind kd-kind--suggéré">suggéré</span> Le modèle lit</b>
<p>Du texte qui entre dans sa fenêtre de contexte. Il le suit presque toujours, mais peut l'oublier ou s'en écarter.</p>
<ul>{lis(["instructions", "regle", "skill"])}<li>la description des outils MCP</li></ul></div>
<div class="br-col br-col--tool"><b><span class="kd-kind kd-kind--imposé">imposé</span> L'outil exécute</b>
<p>Claude Code (ou Kwa) l'applique avant ou après chaque action, sans demander l'avis du modèle.</p>
<ul>{lis(["hook", "permission", "politique"])}<li>la liste <code>tools</code> d'un sous-agent</li></ul></div>
</div>
<p class="kd-note">Une brique « mixte » a les deux : un sous-agent suit son texte, mais ne peut utiliser que les outils permis. Un plugin vaut ce qu'il contient. Page écrite pour Claude Code ; Codex lit le même <code>AGENTS.md</code>, et ses autres emplacements sont dans le <a href="https://github.com/nesyouyou/kwa#claude-code-et-codex">README de Kwa</a>.</p></section>

<section class="br-trip" aria-labelledby="br-trip-h"><h2 id="br-trip-h" class="br-h">Le trajet d'une commande</h2>
<p class="kd-note">L'agent veut lancer <code>git commit</code>. Voici, dans l'ordre, ce qui peut l'arrêter. Chaque étape est une brique.</p>
<ol class="br-steps">
<li class="br-st-model"><b>Le modèle décide</b><span>guidé par les <a href="#instructions">instructions</a>, les <a href="#regle">règles</a> et la <a href="#skill">skill</a> en cours</span></li>
<li class="br-st-tool"><b>Hooks <code>PreToolUse</code></b><span>tous en parallèle ; un refus arrête tout (<a href="#hook">hook</a>, gardes de <a href="#politique">Kwa</a>)</span></li>
<li class="br-st-tool"><b>Permissions</b><span><code>deny</code>, puis <code>ask</code>, puis <code>allow</code>, puis le mode de la session (<a href="#permission">permission</a>)</span></li>
<li class="br-st-os"><b>Bac à sable</b><span>la commande tourne dans les limites du système (<a href="#sandbox">bac à sable</a>)</span></li>
<li class="br-st-tool"><b>Hooks <code>PostToolUse</code></b><span>formater, vérifier : l'action a déjà eu lieu</span></li>
<li class="br-st-model"><b>Le résultat revient</b><span>dans la fenêtre de contexte : le modèle le lit et continue</span></li>
</ol>
<p class="kd-note">Hors de la machine, la <strong>protection de branche</strong> de GitHub refuse encore une fusion sans relecture : le dernier filet, et le plus solide.</p></section>

<section class="br-pick" aria-labelledby="br-pick-h"><h2 id="br-pick-h" class="br-h">Laquelle choisir ?</h2>
<p class="kd-note">Choisissez un besoin, puis faites votre pronostic parmi les briques : la page corrige, avec la raison.</p>
<div class="br-needs">{needs}</div>
<div class="br-guess" id="br-guess" hidden><span>Votre pronostic :</span>{guess}</div>
<p class="br-answer" id="br-answer" aria-live="polite"></p>
<div class="br-forbid"><h3>Interdire quelque chose : trois façons</h3>
<table class="pc-table"><thead><tr><th>Besoin</th><th>Le plus simple</th></tr></thead><tbody>
<tr><td>Une commande ou un fichier toujours interdit, quelle que soit la situation</td><td><a href="#permission">Permission</a> <code>deny</code> : une ligne dans settings.json</td></tr>
<tr><td>Un refus qui dépend du contexte : la branche, le contenu du fichier, l'heure</td><td><a href="#hook">Hook</a> : un script calcule la décision</td></tr>
<tr><td>Un refus propre au projet, avec la raison expliquée à l'agent, sous Claude Code comme sous Codex</td><td><a href="#politique">Politique Kwa</a> : les gardes de Kwa l'appliquent</td></tr></tbody></table></div></section>

<section class="br-where" aria-labelledby="br-where-h"><h2 id="br-where-h">Où tout cela vit</h2>
<p class="kd-note">Un projet qui utilise toutes les briques. Rien n'est obligatoire : la plupart des projets commencent par <code>AGENTS.md</code> et une ou deux règles.</p>
{code(PROJECT_TREE)}</section>

{"".join(card(b) for b in BRICKS)}

<div class="pc-check"><h2>Sources</h2><ul>
<li><a href="{DOC}memory">Fichiers d'instructions et règles</a></li><li><a href="{DOC}skills">Skills</a></li>
<li><a href="{DOC}sub-agents">Sous-agents</a></li><li><a href="{DOC}hooks">Hooks</a></li><li><a href="{DOC}mcp">MCP</a></li>
<li><a href="{DOC}permissions">Permissions</a></li><li><a href="{DOC}plugins">Plugins</a></li></ul></div>
<script type="application/json" id="br-names">{html.escape(json.dumps(names, ensure_ascii=False), quote=False)}</script>"""
