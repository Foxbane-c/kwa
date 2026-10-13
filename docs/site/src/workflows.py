"""Les cinq workflows de Kwa, mis en avant sur l'accueil : chaque workflow est une suite d'étapes typées (skill, garde,
hook, agent, vous, relais), animée par src/workflows.js. Les étapes viennent de src/flows.py, qui sert aussi la page
Les workflows : un seul endroit à tenir à jour."""
from __future__ import annotations

import html

import pictos

from flows import FLOWS, KIND  # une seule source : les étapes viennent des workflows animés

META = [  # (clé, pictogramme, promesse)
    ("feature", "code", "De l'idée floue à une PR prouvée."),
    ("bug", "bug", "Pas de correctif avant la cause."),
    ("review", "eye", "Un regard neuf qui ne peut rien modifier."),
    ("ship", "send", "Chaque publication est une décision."),
    ("learn", "book", "Chaque session enrichit la suivante."),
]
WORKFLOWS = [(k, pic, FLOWS[k]["title"], promise, f"board.html#{k}", [(kind, name, what) for _b, kind, name, what in FLOWS[k]["steps"]])
             for k, pic, promise in META]


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
  <div class="kd-head"><div class="kd-eyebrow">Les workflows</div><h2 class="kw-section-title">Cinq workflows agentiques</h2>
    <p class="kd-lead">Chacun enchaîne des skills, des gardes, des hooks et des agents, et garde vos décisions aux bons
    endroits. Choisissez un workflow pour voir ses étapes.</p></div>
  <div class="wf" id="wf">
    <div class="wf-tabs" role="tablist" aria-label="Workflows">{"".join(tabs)}</div>
    {"".join(panels)}
    <ul class="wf-legend" aria-label="Légende">{legend}</ul>
  </div>
  <script src="src/workflows.js"></script>
</section>"""
