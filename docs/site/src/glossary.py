"""Glossaire du site : les mots du dev agentique, en français, avec le terme anglais d'origine.

Sert deux fois : la page glossaire.html, et les infobulles posées par shell.js sur la première occurrence de chaque
terme dans une page (données dans src/glossary-data.js, généré). Un terme : (id, mot affiché, anglais ou "", autres
formes repérées dans les pages, définition courte, « dans Kwa » ou "").
"""
from __future__ import annotations

import html
import json

TERMS = [
    ("agent", "Agent", "agent", ["agents", "agent de code", "agents de code"],
     "Un modèle de langage qui reçoit un objectif et travaille en boucle : il réfléchit, utilise un outil (lire un fichier, lancer une commande), lit le résultat, puis continue ou s'arrête.",
     "Claude Code et Codex sont des agents de code ; Kwa les encadre."),
    ("dev-agentique", "Dev agentique", "agentic coding", ["développement agentique"],
     "Développer en confiant une partie du travail à un agent de code, qui lit, modifie et exécute dans votre projet pendant que vous cadrez et vérifiez.", ""),
    ("harness", "Harness (harnais)", "harness", [],
     "Tout ce qui entoure le modèle pour qu'il travaille dans votre processus : consignes, garde-fous, procédures, mémoire, vérifications. Le mot vient du harnais d'un cheval.",
     "Kwa est un harness : il ajoute ce cadre à Claude Code et à Codex."),
    ("workflow", "Workflow", "workflow", ["workflows"],
     "Une suite d'étapes pour mener un travail du début à la fin, par exemple de la demande à la pull request.",
     "Kwa en automatise cinq : développer, corriger un bug, relire, livrer, capitaliser."),
    ("skill", "Skill (savoir-faire)", "skill", ["skills"],
     "Une procédure écrite dans un fichier SKILL.md : un en-tête qui dit quand s'en servir, un corps qui dit comment. L'agent la suit quand la situation correspond, ou vous la lancez.",
     "/kwa:commit sous Claude Code, $kwa:commit sous Codex."),
    ("hook", "Hook (crochet)", "hook", ["hooks"],
     "Un script que l'agent lance tout seul à un moment précis : avant une commande, après une modification, au démarrage, à la fin d'une réponse.",
     "Certains hooks de Kwa refusent (les gardes), d'autres automatisent (formatage, journal, rappel des skills)."),
    ("garde", "Garde (garde-fou)", "guard, guardrail", ["gardes", "garde-fou", "garde-fous"],
     "Un hook lancé avant chaque action de l'agent, qui répond : refuser, demander confirmation ou laisser passer. Un filet contre l'erreur, pas une barrière de sécurité.",
     "Exemples : pas de commit sur main, pas de lecture d'un fichier de secrets."),
    ("politique", "Politique du projet", "policy", ["politique"],
     "Le fichier .claude/kwa.policy.json : ce qui change d'un projet à l'autre (commandes interdites ou à confirmer, vérifications, environnements).", ""),
    ("prompt", "Prompt (consigne)", "prompt", ["prompts"],
     "Le texte que l'on donne au modèle pour lui demander quelque chose : la demande, son contexte, le format attendu.", ""),
    ("jeton", "Jeton", "token", ["jetons", "token", "tokens"],
     "Le morceau de texte que le modèle lit et écrit (souvent un bout de mot). Tout se compte en jetons : la taille de la fenêtre, les limites, le coût.", ""),
    ("fenetre", "Fenêtre de contexte", "context window", ["fenêtre"],
     "Tout ce que le modèle peut voir à un instant : consignes, fichiers lus, historique, résultats d'outils. Il n'a pas d'autre mémoire.", ""),
    ("context-engineering", "Context engineering", "context engineering", [],
     "L'art de choisir ce qui entre dans la fenêtre de contexte : le plus petit ensemble d'informations utiles pour obtenir le bon résultat.", ""),
    ("compaction", "Compaction", "compaction", [],
     "Quand la fenêtre se remplit, l'agent résume la conversation pour libérer de la place et continuer.", ""),
    ("hallucination", "Hallucination", "hallucination", ["hallucinations"],
     "Une affirmation fausse produite par le modèle avec le même ton qu'une vraie : une API qui n'existe pas, une source inventée.", ""),
    ("injection", "Injection de prompt", "prompt injection", [],
     "Un texte lu par l'agent (page web, ticket, fichier) qui contient des instructions cachées pour détourner son comportement.", ""),
    ("sous-agent", "Sous-agent", "subagent", ["sous-agents"],
     "Un agent lancé par l'agent principal, avec sa propre fenêtre de contexte : il fait une tâche et ne renvoie qu'un résumé.",
     "Kwa installe kwa:reviewer, un sous-agent en lecture seule."),
    ("handoff", "Handoff (passage de relais)", "handoff", [],
     "Un court document de reprise (objectif, fait, décisions, reste à faire, pièges) pour qu'une autre session ou un autre agent continue sans relire toute la conversation.",
     "/kwa:handoff l'écrit."),
    ("mcp", "MCP", "Model Context Protocol", [],
     "Un protocole commun pour brancher à l'agent des outils externes : documentation, navigateur, base de données, tracker.",
     "Exemples : Context7 (documentation à jour), Playwright (navigateur)."),
    ("sandbox", "Bac à sable", "sandbox", [],
     "Un environnement isolé où les commandes de l'agent ne peuvent pas tout toucher (fichiers, réseau).", ""),
    ("mode-plan", "Mode plan", "plan mode", [],
     "Un mode où l'agent lit et propose un plan sans rien modifier, avant de passer à l'implémentation.", ""),
    ("pr", "Pull request (PR)", "pull request", ["PR", "pull request", "pull requests"],
     "Une demande de fusion d'une branche dans la branche principale, avec sa description, sa relecture et ses vérifications.", ""),
    ("issue", "Issue (ticket)", "issue", ["issues"],
     "Un ticket sur GitHub qui décrit un besoin ou un bug, et auquel une pull request se rattache (« Closes #12 »).", ""),
    ("branche", "Branche", "branch", ["branches"],
     "Une ligne de travail parallèle dans git. On travaille sur une branche, jamais directement sur main.", ""),
    ("worktree", "Worktree", "worktree", ["worktrees"],
     "Un second dossier de travail lié au même dépôt git, sur une autre branche : on travaille sur deux sujets sans se gêner.", ""),
    ("commit", "Commit", "commit", ["commits"],
     "Un enregistrement d'un changement dans l'historique git, avec son message.", ""),
    ("push", "Push (publier)", "push", [],
     "Envoyer ses commits vers le dépôt distant (GitHub). Chez Kwa, publier une branche demande confirmation.", ""),
    ("merge", "Fusion", "merge", ["fusionner"],
     "Intégrer une branche dans une autre, en général une pull request dans main. Décision humaine chez Kwa.", ""),
    ("tdd", "TDD (test d'abord)", "test-driven development", ["test d'abord"],
     "Écrire d'abord un test qui échoue, puis le code qui le fait passer, puis nettoyer.", ""),
    ("adr", "ADR", "architecture decision record", ["ADR"],
     "Une note courte qui consigne une décision d'architecture durable : le contexte, le choix, la raison.", ""),
    ("dry-run", "Simulation", "dry run", ["--dry-run", "dry-run"],
     "Exécuter une commande pour voir ce qu'elle ferait, sans rien modifier.", "kwa init --dry-run."),
    ("ci", "Intégration continue (CI)", "continuous integration", ["CI"],
     "Les vérifications (tests, build) lancées automatiquement à chaque changement poussé.", ""),
]

SKIP_AUTO = {"pr", "ci", "adr", "branche", "commit", "merge", "push", "issue"}  # trop courants pour une infobulle partout


def data_js() -> str:
    items = []
    for tid, label, en, forms, short, kwa in TERMS:
        if tid in SKIP_AUTO:
            continue
        words = [label.split(" (")[0]] + forms
        if en and en.lower() != label.split(" (")[0].lower():
            words.append(en)
        base = label.split(" (")[0]
        tip = f"{label} : {short}" + ((" Mot anglais." if en.lower() == base.lower() else f" En anglais : {en}.") if en else "")
        items.append({"id": tid, "words": sorted(set(words), key=len, reverse=True), "tip": tip})
    return "window.KWA_GLOSSARY=" + json.dumps(items, ensure_ascii=False) + ";\n"


def page() -> str:
    rows = []
    for tid, label, en, _forms, short, kwa in sorted(TERMS, key=lambda t: t[1].lower()):
        en_line = f'<span class="gl-en">anglais : <i>{html.escape(en)}</i></span>' if en else ""
        kwa_line = f'<p class="gl-kwa"><b>Dans Kwa</b> : {html.escape(kwa)}</p>' if kwa else ""
        rows.append(f'<div class="gl-item" id="{tid}" data-text="{html.escape((label + " " + en + " " + short).lower())}">'
                    f'<h2>{html.escape(label)}</h2>{en_line}<p>{html.escape(short)}</p>{kwa_line}</div>')
    return f"""<p class="kw-lead gl-lead">Le dev agentique arrive avec beaucoup de mots anglais. Voici chacun, en français, avec
son terme d'origine. Sur les autres pages, survolez un mot souligné en pointillés pour voir sa définition.</p>
<input class="gl-search" id="gl-search" type="search" placeholder="Chercher un terme, en français ou en anglais…" aria-label="Chercher un terme">
<div class="gl-list" id="gl-list">{"".join(rows)}</div>
<p class="kd-note" id="gl-none" hidden>Aucun terme ne correspond.</p>
<script>(function(){{var i=document.getElementById('gl-search'),items=document.querySelectorAll('.gl-item'),none=document.getElementById('gl-none');
i.addEventListener('input',function(){{var q=i.value.trim().toLowerCase(),n=0;Array.prototype.forEach.call(items,function(it){{var ok=!q||it.getAttribute('data-text').indexOf(q)>-1;it.hidden=!ok;if(ok)n++;}});none.hidden=n>0;}});}})();</script>"""
