"""Page « Skills qui délèguent » : comment /kwa-agents, /kwa-parallel et /kwa-review confient du travail à des agents
neufs, à partir d'un modèle de prompt rempli. Le schéma est animé par src/delegation.js."""
from __future__ import annotations

import html

import pictos

STATIONS = [  # (clé, pictogramme, titre, sous-titre)
    ("skill", "sword", "La skill", "dans la session principale"),
    ("prompt", "doc", "Le prompt", "un modèle, rempli pour la tâche"),
    ("agents", "agent", "Les agents", "neufs, sans la conversation"),
    ("report", "doc", "Ce qui revient", "un rapport court"),
    ("check", "shield", "La vérification", "avant de dire « fait »"),
]


def widget() -> str:
    st = "".join(
        f'<li class="dg-st" data-st="{k}"><div class="dg-head">{pictos.svg(p)}<div><b>{html.escape(t)}</b>'
        f'<small>{html.escape(s)}</small></div></div><div class="dg-body"></div></li>'
        for k, p, t, s in STATIONS)
    return f"""<div class="dg" id="dg">
<div class="dg-bar" role="group" aria-label="Choisir une skill">
<button type="button" class="kd-copy" data-dg="agents" aria-pressed="true">/kwa-agents</button>
<button type="button" class="kd-copy" data-dg="parallel" aria-pressed="false">/kwa-parallel</button>
<button type="button" class="kd-copy" data-dg="review" aria-pressed="false">/kwa-review</button>
<span class="dg-sp"></span>
<button type="button" class="kd-copy" data-dg-play>Lecture</button>
<button type="button" class="kd-copy" data-dg-next>Étape suivante</button></div>
<ol class="dg-line">{st}</ol>
<p class="dg-cap" id="dg-cap" aria-live="polite"></p>
</div>"""


ROWS = [
    ("/kwa-agents", "Un plan dont les tâches sont assez indépendantes", "implementer-prompt.md, puis spec-reviewer-prompt.md et quality-reviewer-prompt.md",
     "Un implémenteur neuf par tâche, puis deux relectures par kwa-relecteur", "L'une après l'autre"),
    ("/kwa-parallel", "Plusieurs problèmes sans fichier ni état en commun", "agent-prompt.md, un exemplaire par problème",
     "Un agent par problème", "En même temps"),
    ("/kwa-review", "Un diff ou une branche à relire", "reviewer-prompt.md", "kwa-relecteur, en lecture seule", "Un seul par passe"),
]


def page() -> str:
    rows = "".join(f"<tr><td><code>{html.escape(a)}</code></td><td>{html.escape(b)}</td><td>{html.escape(c)}</td>"
                   f"<td>{html.escape(d)}</td><td>{html.escape(e)}</td></tr>" for a, b, c, d, e in ROWS)
    return f"""<p class="kw-lead dg-lead">Trois skills ne font pas tout le travail elles-mêmes : elles le confient à des
<strong>agents neufs</strong>. Un agent neuf ne voit pas la conversation. Tout ce qu'il sait, c'est le
<strong>prompt</strong> que la skill lui écrit à partir d'un modèle rangé avec elle. La qualité du travail délégué
dépend donc de ce prompt, et la skill garde toujours la vérification finale.</p>
{widget()}
<h2 class="kw-section-title dg-h">Qui délègue quoi</h2>
<div class="kd-wrap"><table class="dg-table"><thead><tr><th>Skill</th><th>Quand</th><th>Modèle de prompt</th><th>Agent</th><th>Rythme</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h2 class="kw-section-title dg-h">Ce que contient un prompt délégué</h2>
<div class="kd-grid kd-g2 dg-grid">
<div class="kd-card"><h3>Ce qu'il doit savoir</h3><p>La demande d'origine et ses <strong>critères de réussite</strong>, cités et non résumés ; les <strong>fichiers</strong> à lire ; les erreurs exactes collées ; ce qui est volontairement hors sujet.</p></div>
<div class="kd-card"><h3>Ce qu'il doit rendre</h3><p>Un <strong>format de retour</strong> fixe : ce qui a été fait, les commandes lancées et leur résultat, les fichiers touchés, ce qui reste douteux. Court, pour ne pas remplir la fenêtre de la session.</p></div>
<div class="kd-card"><h3>Ce qu'il ne doit pas faire</h3><p>Pas de commit ni de push, pas d'autre agent lancé, aucun garde-fou contourné : un refus se rapporte tel quel. Le relecteur, lui, ne peut <strong>rien écrire</strong> : c'est l'outil qui l'en empêche.</p></div>
<div class="kd-card"><h3>Ce que la session garde</h3><p>La décision. Un rapport d'agent n'est pas une preuve : la session relance elle-même les <strong>vérifications du projet</strong> avant de dire « fait », et c'est vous qui validez.</p></div>
</div>
<h2 class="kw-section-title dg-h">Sous Claude Code et sous Codex</h2>
<div class="kd-wrap"><table class="dg-table"><thead><tr><th></th><th>Claude Code</th><th>Codex</th></tr></thead><tbody>
<tr><td>Lancer un agent</td><td>Outil <code>Agent</code>, <code>subagent_type</code> (<code>general-purpose</code>, <code>kwa-relecteur</code>)</td><td>En clair : « lance un agent <code>worker</code> avec ce prompt », ou <code>kwa-relecteur</code></td></tr>
<tr><td>Plusieurs à la fois</td><td>Plusieurs appels dans un seul message, en arrière-plan</td><td>Une demande qui lance plusieurs agents et attend tous les résultats</td></tr>
<tr><td>Isoler les écritures</td><td><code>isolation: "worktree"</code> pour des zones voisines</td><td>Pas d'isolation documentée : les tâches voisines passent l'une après l'autre</td></tr>
<tr><td>Relecture en lecture seule</td><td>Outils d'écriture retirés, shell filtré par un hook</td><td>Bac à sable en lecture seule</td></tr>
</tbody></table></div>
<p class="kd-note">Les modèles de prompt sont des fichiers de chaque skill : <a href="skill-map.html#view=pack&node=s:agents">/kwa-agents</a>, <a href="skill-map.html#view=pack&node=s:parallel">/kwa-parallel</a>, <a href="skill-map.html#view=pack&node=s:review">/kwa-review</a> sur la carte.</p>"""
