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
    "agent": ("agent", "Sous-agent"),
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
        "end": "De l'intention floue à la PR fusionnée, puis la leçon rangée.",
        "steps": [
            ("cadrer", "skill", "/kwa:brainstorm", "explorer, comparer deux ou trois approches, écrire une spec courte"),
            ("cadrer", "vous", "validation", "vous approuvez la spec"),
            ("cadrer", "skill", "/kwa:plan", "découper en tâches de quelques minutes"),
            ("faire", "garde", "guard-write", "pas de code produit sur main"),
            ("faire", "skill", "/kwa:start-dev", "issue, branche et worktree"),
            ("faire", "skill", "/kwa:agents", "un implémenteur par tâche"),
            ("prouver", "skill", "/kwa:tdd", "dans chaque implémenteur : un test qui échoue, puis le code"),
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
    "bug": {
        "title": "Corriger un bug",
        "end": "Cause trouvée avant le correctif, preuve qu'il tient, piège rangé pour la suite.",
        "steps": [
            ("cadrer", "skill", "/kwa:debug", "reproduire, remonter à la cause racine"),
            ("cadrer", "vous", "cause", "vous validez la cause avant tout correctif"),
            ("faire", "skill", "/kwa:start-dev", "issue du bug et branche dédiée"),
            ("prouver", "skill", "/kwa:tdd", "un test rouge qui montre le bug"),
            ("prouver", "skill", "/kwa:simple", "le correctif le plus petit possible"),
            ("prouver", "hook", "verify-stop", "refuse de rendre la main sur du rouge, s'il est activé (KWA_STOP_VERIFY=1)"),
            ("prouver", "skill", "/kwa:verify", "le test repasse au rouge sans le correctif"),
            ("livrer", "skill", "/kwa:commit", "un commit qui dit pourquoi"),
            ("livrer", "garde", "guard-github", "une PR se rattache à son issue"),
            ("livrer", "skill", "/kwa:ship", "la PR, avec la preuve"),
            ("capitaliser", "skill", "/kwa:learn", "le piège rangé pour la suite"),
        ],
        "script": [
            ("go", 0, "Symptôme : avec PROMO10, un panier de 30 € coûte 28 € au lieu de 27 €. /kwa:debug reproduit avant de toucher au code."),
            ("loop", 0, 0, "Première hypothèse fausse : l'arrondi n'y est pour rien. On remonte plus loin."),
            ("go", 0, "Cause trouvée : la remise ne s'applique qu'au premier article."),
            ("ask", 1, "La cause vous paraît juste ?", [("Valider", "next"), ("Creuser", ("loop", 0, "On reprend le diagnostic."))], 0,
             "Cause validée : on peut corriger."),
            ("go", 2, "/kwa:start-dev ouvre l'issue du bug et sa branche."),
            ("go", 3, "Un test reproduit le bug : il est rouge, comme attendu."),
            ("go", 4, "Le correctif tient en une ligne."),
            ("guard", 5, "STOP BLOQUÉ — `python3 -m unittest` est rouge. Corriger avant de rendre la main.",
             "L'agent veut rendre la main, mais un test voisin casse : le hook l'en empêche."),
            ("loop", 5, 4, "Un test voisin casse : le correctif est revu."),
            ("go", 6, "/kwa:verify : le test passe, et repasse au rouge si on retire le correctif."),
            ("go", 7, "Un commit, avec la raison du changement."),
            ("guard", 8, "Kwa — Une PR se rattache à son issue : le corps doit porter « Closes #N ».",
             "La PR part sans « Closes #N » (N, le numéro de l'issue sur GitHub) : refusée."),
            ("go", 9, "/kwa:ship ouvre la PR liée à l'issue, avec la sortie des tests."),
            ("go", 10, "/kwa:learn propose de ranger le piège : la remise s'applique ligne par ligne."),
        ],
    },
    "review": {
        "title": "Relire",
        "end": "Un regard neuf qui n'a rien modifié, des constats triés, une décision qui reste la vôtre.",
        "steps": [
            ("relire", "skill", "/kwa:review", "rassembler le diff, la demande et ses critères"),
            ("relire", "agent", "kwa:reviewer", "un regard neuf, en lecture seule"),
            ("relire", "hook", "readonly-bash", "le relecteur ne peut rien modifier"),
            ("relire", "skill", "/kwa:review-feedback", "trier les constats avant d'en appliquer un"),
            ("faire", "skill", "/kwa:tdd", "corriger les constats retenus, test d'abord"),
            ("prouver", "skill", "/kwa:verify", "les vérifications repassent"),
            ("livrer", "vous", "décision", "vous jugez que c'est prêt"),
        ],
        "script": [
            ("go", 0, "/kwa:review rassemble le diff de la branche, la demande d'origine et ses critères de réussite."),
            ("delegate", 1, [("kwa:reviewer", "le diff et les critères", "1 constat critique, 2 mineurs")],
             "Un relecteur neuf relit sans connaître la conversation : il ne voit que ce qu'on lui donne."),
            ("guard", 2, "Kwa — relecteur en lecture seule : sed -i modifie le fichier. Rapporter le besoin au lieu de modifier.",
             "Le relecteur tente de corriger lui-même un fichier : refusé, il doit seulement rapporter."),
            ("go", 3, "/kwa:review-feedback trie : le constat critique et un mineur sont fondés, l'autre est écarté avec sa raison."),
            ("go", 4, "Les constats retenus sont corrigés, chacun avec son test."),
            ("go", 5, "Les vérifications repassent au vert."),
            ("loop", 5, 1, "Les corrections repassent en relecture."),
            ("delegate", 1, [("kwa:reviewer", "les seules corrections", "rien à redire")], "Relecture ciblée des corrections : rien à redire."),
            ("ask", 6, "La branche vous paraît prête ?", [("Prête", "next"), ("Encore une passe", ("loop", 1, "Une passe de relecture de plus."))], 0,
             "Vous jugez que c'est prêt : la livraison peut commencer."),
        ],
    },
    "ship": {
        "title": "Livrer",
        "end": "Chaque publication a été une décision : push, fusion, déploiement vérifié.",
        "steps": [
            ("prouver", "skill", "/kwa:verify", "vérifications du projet, sorties citées"),
            ("livrer", "skill", "/kwa:commit", "un commit par changement logique"),
            ("livrer", "garde", "guard-git", "pas de push sur main"),
            ("livrer", "vous", "push", "vous autorisez la publication de la branche"),
            ("livrer", "garde", "guard-github", "pas de fusion sans preuve"),
            ("livrer", "vous", "fusion", "vous donnez le feu vert"),
            ("livrer", "skill", "/kwa:deploy", "pré-vol, déploiement, vérification"),
            ("capitaliser", "skill", "/kwa:learn", "ce que le déploiement a appris"),
        ],
        "script": [
            ("go", 0, "/kwa:verify lance les vérifications du projet et cite leur sortie."),
            ("loop", 0, 0, "Le lint est rouge : on corrige, puis on relance."),
            ("go", 1, "/kwa:commit fait un commit par changement logique, jamais deux sujets dans le même."),
            ("guard", 2, "Kwa — push direct vers main refusé : pousser la branche de travail et ouvrir une PR",
             "L'agent tente de pousser sur main : refusé."),
            ("go", 3, "Il pousse la branche de travail : la publication sort de votre machine."),
            ("ask", 3, "Autoriser git push sur la branche ?", [("Autoriser", "next"), ("Refuser", ("loop", 1, "Vous voulez revoir les commits."))], 0,
             "Push autorisé : la PR s'ouvre, liée à son issue."),
            ("guard", 4, "Kwa — Aucune preuve sur la PR ni sur ses issues (#14). Joindre les captures ou la sortie des tests.",
             "La fusion est demandée sans preuve : refusée."),
            ("go", 4, "Les captures et la sortie des tests sont jointes : la fusion devient possible."),
            ("ask", 5, "Fusionner la PR ?", [("Fusionner", "next"), ("Pas encore", ("loop", 4, "La PR attend votre relecture."))], 0,
             "Vous fusionnez : la production va être déployée."),
            ("go", 6, "/kwa:deploy fait le pré-vol, déploie, puis vérifie la révision réellement servie."),
            ("go", 7, "/kwa:learn range ce que ce déploiement a appris."),
        ],
    },
    "learn": {
        "title": "Capitaliser",
        "end": "Ce que la session a appris est rangé, et la suivante repart de là.",
        "steps": [
            ("cadrer", "hook", "memory-context", "au démarrage, la reprise de la session précédente"),
            ("faire", "hook", "signal-prompt", "note vos corrections et vos « retiens : »"),
            ("faire", "garde", "guard-write", "un refus devient un signal d'apprentissage"),
            ("capitaliser", "hook", "memory-nudge", "propose de faire le point, une fois par session"),
            ("capitaliser", "skill", "/kwa:learn", "range chaque leçon au bon endroit"),
            ("capitaliser", "vous", "accord", "rien n'est écrit sans vous"),
            ("capitaliser", "doc", "/kwa:handoff", "un document de reprise pour la session suivante"),
        ],
        "script": [
            ("go", 1, "Vous corrigez l'agent : « retiens : les tests se lancent avec pytest ». Le hook note la phrase."),
            ("guard", 2, "Kwa — Pas de code sur main : ouvrir d'abord l'issue et sa branche (/kwa:start-dev), puis travailler dans le worktree créé.",
             "Un garde refuse une écriture sur main : ce refus devient aussi un signal."),
            ("go", 3, "En fin de session, le hook propose une seule fois de faire le point."),
            ("go", 4, "/kwa:learn trie notes et signaux : deux leçons valent d'être gardées."),
            ("ask", 5, "Ranger ces deux leçons ?", [("Tout ranger", "next"), ("Seulement la première", ("loop", 4, "On n'en garde qu'une."))], 0,
             "Vous validez : chaque leçon va à sa place (pièges du projet, politique)."),
            ("handoff", 6, "/kwa:handoff écrit le document de reprise de la session."),
            ("loop", 6, 0, "Session suivante : on repart du cadrage, avec ce qui a été appris."),
            ("go", 0, "Au démarrage, le hook remet le journal et les leçons dans le contexte de l'agent."),
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
    return f"""<div class="fl" id="fl-{key}" data-flow="{key}" data-end="{html.escape(flow["end"])}">
  <div class="fl-bar">
    {shell.player("Lecture du workflow")}
    <p class="fl-say" aria-live="polite">Lisez le workflow d'une traite, ou pas à pas avec les flèches : ses boucles, vos décisions et les refus des gardes.</p>
  </div>
  <div class="fl-board"><div class="fl-row">{"".join(cols)}</div><div class="fl-rail" aria-hidden="true"><i class="fl-fill"></i></div>
    <span class="fl-token" aria-hidden="true"></span><svg class="fl-arcs" aria-hidden="true"></svg></div>
  <ul class="fl-legend" aria-label="Légende">{legend}</ul>
  <p class="fl-note">Garde et hook : imposés, l'outil les exécute. Skill et agent : suggérés, le modèle décide de les suivre. <a href="impose.html">Ce qui est imposé, ce qui est suggéré</a></p>
  <script type="application/json" class="fl-script">{_json(key)}</script>
</div>"""


def section() -> str:
    """Les cinq workflows : un onglet par workflow, chacun avec son lecteur (un seul visible à la fois)."""
    import workflows
    icon = {key: pic for key, pic, *_ in workflows.WORKFLOWS}
    keys = [k for k, *_ in workflows.WORKFLOWS if k in FLOWS]
    tabs = "".join(
        f'<button type="button" class="wf-tab" role="tab" id="fl-tab-{k}" aria-controls="fl-panel-{k}" aria-selected="{"true" if i == 0 else "false"}" '
        f'data-flow-tab="{k}">{pictos.svg(icon[k])}<span>{html.escape(FLOWS[k]["title"])}</span></button>'
        for i, k in enumerate(keys))
    panels = "".join(
        f'<div class="fl-panel" role="tabpanel" id="fl-panel-{k}" aria-labelledby="fl-tab-{k}" data-flow-panel="{k}"{"" if i == 0 else " hidden"}>{player(k)}</div>'
        for i, k in enumerate(keys))
    return f'<div class="fl-picker"><div class="wf-tabs" role="tablist" aria-label="Choisir un workflow">{tabs}</div>{panels}</div>'
