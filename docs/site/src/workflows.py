"""Les cinq workflows de Kwa, mis en avant sur l'accueil : chaque workflow est une suite d'étapes typées (skill, garde,
hook, agent, vous), animée par src/workflows.js. Les données sont ici ; un test vérifie que chaque skill citée existe."""
from __future__ import annotations

import html

import pictos

KIND = {  # type d'étape -> (pictogramme, libellé)
    "skill": ("sword", "Skill"),
    "garde": ("shield", "Garde"),
    "hook": ("hook", "Hook"),
    "agent": ("agent", "Agent"),
    "vous": ("user", "Vous"),
}

WORKFLOWS = [  # (clé, pictogramme, titre, promesse, lien, [(type, nom, ce qui se passe)])
    ("feature", "code", "Développer une fonctionnalité", "De l'idée floue à une PR prouvée.", "board.html#detail", [
        ("skill", "/kwa:brainstorm", "cadrer l'intention, écrire une spec courte"),
        ("vous", "validation", "vous approuvez la spec"),
        ("skill", "/kwa:plan", "découper en tâches de quelques minutes"),
        ("skill", "/kwa:start-dev", "ouvrir l'issue, la branche et son worktree"),
        ("garde", "guard-write", "refuse le code produit sur main"),
        ("skill", "/kwa:tdd", "test qui échoue, puis le code"),
        ("agent", "kwa:relecteur", "relit en lecture seule"),
        ("skill", "/kwa:ship", "PR liée à son issue, avec la preuve"),
    ]),
    ("bug", "bug", "Corriger un bug", "Pas de correctif avant la cause.", "skill-map.html#view=bug", [
        ("skill", "/kwa:debug", "reproduire, remonter à la cause racine"),
        ("skill", "/kwa:start-dev", "issue et branche dédiée"),
        ("skill", "/kwa:tdd", "un test rouge qui montre le bug"),
        ("skill", "/kwa:simple", "le correctif le plus petit possible"),
        ("skill", "/kwa:verify", "preuve : le test repasse au rouge sans le correctif"),
        ("hook", "verify-stop", "refuse de finir sur des tests rouges"),
    ]),
    ("review", "eye", "Relire", "Un regard neuf qui ne peut rien modifier.", "delegation.html", [
        ("skill", "/kwa:review", "rassembler le diff et les critères"),
        ("agent", "kwa:relecteur", "constats classés et verdict, en lecture seule"),
        ("skill", "/kwa:review-feedback", "trier les retours avant d'en appliquer un"),
        ("agent", "kwa:relecteur", "relecture ciblée des corrections"),
        ("vous", "décision", "vous jugez que c'est prêt"),
    ]),
    ("ship", "send", "Livrer", "Chaque publication est une décision.", "skill-map.html#view=delivery", [
        ("skill", "/kwa:verify", "vérifications du projet, sorties citées"),
        ("skill", "/kwa:commit", "un commit par changement logique"),
        ("garde", "guard-git", "pas de push sur main, push de branche confirmé"),
        ("garde", "guard-github", "PR liée à une issue, fusion avec preuve"),
        ("vous", "fusion", "vous donnez le feu vert"),
        ("skill", "/kwa:deploy", "pré-vol, déploiement, vérification"),
    ]),
    ("learn", "book", "Capitaliser", "Chaque session enrichit la suivante.", "memoire.html", [
        ("hook", "signal-prompt", "note vos corrections et vos « retiens : »"),
        ("garde", "refus d'un garde", "devient un signal d'apprentissage"),
        ("hook", "memory-nudge", "propose de capitaliser, une fois par session"),
        ("skill", "/kwa:learn", "range chaque leçon au bon endroit"),
        ("vous", "accord", "rien n'est écrit sans vous"),
        ("hook", "memory-context", "au démarrage suivant, la reprise"),
    ]),
]


def section() -> str:
    tabs, panels = [], []
    for i, (key, pic, title, promise, link, steps) in enumerate(WORKFLOWS):
        on = "true" if i == 0 else "false"
        tabs.append(f'<button type="button" class="wf-tab" role="tab" aria-selected="{on}" data-wf="{key}">'
                    f'{pictos.svg(pic)}<span>{html.escape(title)}</span></button>')
        items = "".join(
            f'<li class="wf-step wf-{kind}" style="--i:{n}"><span class="wf-dot">{pictos.svg(KIND[kind][0])}</span>'
            f'<b>{html.escape(name)}</b><small>{html.escape(what)}</small><em>{KIND[kind][1]}</em></li>'
            for n, (kind, name, what) in enumerate(steps))
        panels.append(f'<div class="wf-panel" role="tabpanel" data-panel="{key}"{"" if i == 0 else " hidden"}>'
                      f'<p class="wf-promise">{html.escape(promise)} <a href="{link}">Voir en détail →</a></p>'
                      f'<ol class="wf-steps">{items}</ol></div>')
    legend = "".join(f'<li class="wf-{k}"><span class="wf-dot">{pictos.svg(p)}</span>{lab}</li>' for k, (p, lab) in KIND.items())
    return f"""<section class="kw-container kd-section kd-rv" id="workflows">
  <div class="kd-head"><div class="kd-eyebrow">Les workflows</div><h2 class="kw-section-title">Cinq workflows automatisés</h2>
    <p class="kd-lead">Chacun enchaîne des skills, des gardes, des hooks et des agents, et garde vos décisions aux bons
    endroits. Choisissez un workflow pour voir ses étapes.</p></div>
  <div class="wf" id="wf">
    <div class="wf-tabs" role="tablist" aria-label="Workflows">{"".join(tabs)}</div>
    {"".join(panels)}
    <ul class="wf-legend" aria-label="Légende">{legend}</ul>
  </div>
  <script src="src/workflows.js"></script>
</section>"""
