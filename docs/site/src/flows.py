"""Workflows animés : chaque workflow est un schéma de briques (Cadrer, Faire, Prouver, Relire, Livrer, Capitaliser),
chaque brique liste ses étapes, et un scénario fait avancer un jeton d'étape en étape. Le scénario porte ce qui rend
un workflow vivant : les boucles quand une condition n'est pas remplie, vos décisions (une mini-fenêtre), les refus
des gardes, les skills qui délèguent à des sous-agents, les passages de relais.

Les données sont ici ; le rendu HTML statique (lisible sans animation) aussi ; src/flows.js anime. Un test vérifie que
chaque skill, garde et agent nommé existe, et que chaque événement vise une étape réelle.
"""
from __future__ import annotations

import html
import json

import pictos
import shell

BRICKS = [  # (id, libellé, ce que la brique garantit)
    ("cadrer", "Cadrer", "savoir quoi faire avant de le faire"),
    ("faire", "Faire", "sur une branche, par petites tâches"),
    ("prouver", "Prouver", "une sortie fraîche, pas une impression"),
    ("relire", "Relire", "un regard neuf qui ne peut rien modifier"),
    ("livrer", "Livrer", "chaque publication est une décision"),
    ("capitaliser", "Capitaliser", "la session suivante part de ce qu'on a appris"),
]

KIND = {  # type d'étape -> (pictogramme, libellé)
    "skill": ("sword", "Skill"),
    "garde": ("shield", "Garde"),
    "hook": ("hook", "Hook"),
    "agent": ("agent", "Agent"),
    "vous": ("user", "Vous"),
    "doc": ("doc", "Relais"),
}

# Un workflow : ses étapes (brique, type, nom, ce qui se passe) et son scénario. Événements du scénario :
#   ("go", étape, narration)                       le jeton arrive sur l'étape
#   ("guard", étape, message, narration)           un garde refuse ; le message est celui du garde
#   ("ask", étape, question, [options], choix, narration)
#        option : (libellé, suite) ; suite = "next" ou ("loop", étape, raison) ; choix = indice retenu par le scénario
#   ("loop", de, vers, raison)                     une condition n'est pas remplie : retour en arrière
#   ("delegate", étape, [(agent, tâche, retour)], narration)
#   ("handoff", étape, narration)                  un document de reprise passe à la session suivante
FLOWS = {
    "feature": {
        "title": "Développer une fonctionnalité",
        "steps": [
            ("cadrer", "skill", "/kwa:brainstorm", "explorer, comparer deux ou trois approches, écrire une spec courte"),
            ("cadrer", "vous", "validation", "vous approuvez la spec"),
            ("cadrer", "skill", "/kwa:plan", "découper en tâches de quelques minutes"),
            ("faire", "garde", "guard-write", "pas de code produit sur main"),
            ("faire", "skill", "/kwa:start-dev", "issue, branche et worktree"),
            ("faire", "skill", "/kwa:agents", "un implémenteur par tâche"),
            ("prouver", "skill", "/kwa:tdd", "un test qui échoue, puis le code"),
            ("prouver", "skill", "/kwa:verify", "les vérifications du projet, sorties citées"),
            ("relire", "agent", "kwa:reviewer", "relit en lecture seule"),
            ("relire", "skill", "/kwa:review-feedback", "trier les constats avant d'en appliquer un"),
            ("livrer", "vous", "push", "vous autorisez la publication de la branche"),
            ("livrer", "skill", "/kwa:ship", "PR liée à son issue, avec la preuve"),
            ("livrer", "vous", "fusion", "vous donnez le feu vert"),
            ("capitaliser", "skill", "/kwa:learn", "ranger chaque leçon au bon endroit"),
            ("capitaliser", "doc", "/kwa:handoff", "un document de reprise pour la session suivante"),
        ],
        "script": [
            ("go", 0, "L'intention est encore floue : /kwa:brainstorm explore le code et propose deux ou trois approches."),
            ("go", 1, "La spec est prête. C'est à vous de dire si elle correspond à ce que vous voulez."),
            ("ask", 1, "La spec vous convient ?", [("Approuver", "next"), ("Revoir", ("loop", 0, "Il manque un cas : on reprend le cadrage."))], 1,
             "Vous demandez une retouche : retour au cadrage."),
            ("go", 0, "Le cadrage reprend avec votre remarque, puis la spec revient vers vous."),
            ("go", 1, "Deuxième version de la spec."),
            ("ask", 1, "La spec vous convient ?", [("Approuver", "next"), ("Revoir", ("loop", 0, "On reprend le cadrage."))], 0,
             "Spec approuvée : on peut planifier."),
            ("go", 2, "/kwa:plan découpe la spec en tâches courtes, avec leurs fichiers et leurs tests."),
            ("guard", 3, "Kwa — Pas de code sur main : ouvrir d'abord l'issue et sa branche (/kwa:start-dev), puis travailler dans le worktree créé.",
             "L'agent essaie d'écrire dans src/ sur main : le garde l'arrête et indique la bonne voie."),
            ("go", 4, "/kwa:start-dev ouvre l'issue, crée la branche et son worktree."),
            ("delegate", 5, [("implémenteur", "tâche 1", "fait, test vert"), ("implémenteur", "tâche 2", "fait, test vert"),
                             ("implémenteur", "tâche 3", "fait, test vert")],
             "/kwa:agents confie chaque tâche à un sous-agent neuf, qui revient avec un résumé."),
            ("go", 6, "Chaque comportement commence par un test qui échoue."),
            ("loop", 6, 6, "Le cas limite échoue encore : on corrige, et le test repasse."),
            ("go", 7, "/kwa:verify lance les vérifications du projet et cite leur sortie."),
            ("delegate", 8, [("kwa:reviewer", "le diff de la branche", "2 constats importants")],
             "Un relecteur en lecture seule relit toute la branche."),
            ("go", 9, "/kwa:review-feedback trie les constats : deux sont fondés."),
            ("loop", 9, 6, "Deux constats à corriger : retour au test et au code."),
            ("go", 6, "Les corrections passent par un test, comme le reste."),
            ("go", 7, "Les vérifications repassent au vert."),
            ("delegate", 8, [("kwa:reviewer", "les corrections", "prêt")], "Relecture ciblée des corrections : rien à redire."),
            ("go", 10, "Publier la branche sort de votre machine : on vous le demande."),
            ("ask", 10, "Autoriser git push sur la branche ?", [("Autoriser", "next"), ("Refuser", ("loop", 7, "Vous voulez revoir avant de publier."))], 0,
             "Vous autorisez le push de la branche."),
            ("go", 11, "/kwa:ship ouvre la PR, liée à son issue, avec la sortie des vérifications."),
            ("go", 12, "La fusion reste votre décision."),
            ("ask", 12, "Fusionner la PR ?", [("Fusionner", "next"), ("Pas encore", ("loop", 11, "La PR attend votre relecture."))], 0,
             "Vous fusionnez."),
            ("go", 13, "/kwa:learn propose ce qui mérite d'être retenu ; rien n'est écrit sans votre accord."),
            ("handoff", 14, "/kwa:handoff écrit un document de reprise : la prochaine session repart de là."),
        ],
    },
}


def check(flow: dict) -> list[str]:
    """Erreurs de cohérence d'un scénario (étape inexistante, choix hors options)."""
    n, errs = len(flow["steps"]), []
    ok = lambda i: isinstance(i, int) and 0 <= i < n  # noqa: E731
    for ev in flow["script"]:
        kind = ev[0]
        targets = [ev[1]] + ([ev[2]] if kind == "loop" else [])
        if kind == "ask":
            for _label, then in ev[3]:
                if then != "next":
                    targets.append(then[1])
            if not 0 <= ev[4] < len(ev[3]):
                errs.append(f"choix hors options : {ev}")
        errs += [f"étape inexistante {t} dans {ev[:2]}" for t in targets if not ok(t)]
    return errs


def _json(key: str) -> str:
    flow = FLOWS[key]
    out = []
    for ev in flow["script"]:
        kind = ev[0]
        if kind == "go":
            out.append({"t": "go", "at": ev[1], "say": ev[2]})
        elif kind == "guard":
            out.append({"t": "guard", "at": ev[1], "msg": ev[2], "say": ev[3]})
        elif kind == "loop":
            out.append({"t": "loop", "at": ev[1], "to": ev[2], "say": ev[3]})
        elif kind == "ask":
            opts = [{"label": l, "next": t == "next", "to": None if t == "next" else t[1], "why": None if t == "next" else t[2]}
                    for l, t in ev[3]]
            out.append({"t": "ask", "at": ev[1], "q": ev[2], "opts": opts, "pick": ev[4], "say": ev[5]})
        elif kind == "delegate":
            out.append({"t": "delegate", "at": ev[1], "agents": [{"who": a, "task": t, "back": b} for a, t, b in ev[2]], "say": ev[3]})
        elif kind == "handoff":
            out.append({"t": "handoff", "at": ev[1], "say": ev[2]})
    return json.dumps(out, ensure_ascii=False)


def player(key: str) -> str:
    """Le schéma d'un workflow (statique et complet) et son scénario pour l'animation."""
    flow = FLOWS[key]
    cols = []
    for bid, label, promise in BRICKS:
        items = "".join(
            f'<li class="fl-node fl-{kind}" data-i="{i}"><span class="fl-dot">{pictos.svg(KIND[kind][0])}</span>'
            f'<span class="fl-txt"><b>{html.escape(name)}</b><small>{html.escape(what)}</small></span></li>'
            for i, (b, kind, name, what) in enumerate(flow["steps"]) if b == bid)
        if items:
            minis = "".join(f'<i class="fl-mini fl-{kind}" title="{html.escape(name)}">{pictos.svg(KIND[kind][0])}</i>'
                            for b, kind, name, _w in flow["steps"] if b == bid)
            cols.append(f'<section class="fl-brick" data-b="{bid}"><header><span class="fl-n">{len(cols) + 1}</span>'
                        f'<h3>{html.escape(label)}</h3><p>{html.escape(promise)}</p><span class="fl-minis">{minis}</span></header>'
                        f'<div class="fl-body"><ol>{items}</ol><div class="fl-tray" aria-hidden="true"></div></div></section>')
    legend = "".join(f'<li class="fl-{k}"><span class="fl-dot">{pictos.svg(p)}</span>{lab}</li>' for k, (p, lab) in KIND.items())
    return f"""<div class="fl" id="fl-{key}" data-flow="{key}">
  <div class="fl-bar">
    {shell.player("Lecture du workflow")}
    <p class="fl-say" aria-live="polite">Lisez le workflow d'une traite, ou pas à pas avec les flèches : ses boucles, vos décisions et les refus des gardes.</p>
  </div>
  <div class="fl-board"><div class="fl-row">{"".join(cols)}</div><div class="fl-rail" aria-hidden="true"><i class="fl-fill"></i></div>
    <span class="fl-token" aria-hidden="true"></span><svg class="fl-arcs" aria-hidden="true"></svg></div>
  <ul class="fl-legend" aria-label="Légende">{legend}</ul>
  <script type="application/json" class="fl-script">{_json(key)}</script>
</div>"""
