"""Page « Le Mod » : le mod kwa-activity (mods/kwa-activity), qui dessine le workflow en cours et le coût de la session.

Les couleurs et les états décrits ici sont ceux de mods/kwa-activity/hooks/workflow.ts ; un test vérifie que les
libellés cités y figurent toujours.
"""
from __future__ import annotations

from parcours import cmd, code

INSTALL = "/plugin install kwa-activity@kwa"
TOGGLE = "/kwa-activity"
# libellés repris tels quels du dessin (mods/kwa-activity/hooks/workflow.ts)
LABELS = ["en cours", "passée", "refusé", "interrompue", "en parallèle", "coût de la session"]

STATES = [  # (pastille, nom, ce que ça veut dire)
    ("pn-done", "Faite", "L'étape a eu lieu et s'est terminée : coche verte et sa durée."),
    ("pn-run", "En cours", "La boîte est teintée, sa bordure pulse, avec « en cours » et le temps écoulé."),
    ("pn-spin", "Sous-agent", "Un moulinet tourne tant qu'il travaille ; plusieurs agents d'une brique font une seule boîte « ×N »."),
    ("pn-deny", "Refusée", "Un garde de Kwa a refusé l'action : boîte rouge et croix. Dix refus du même garde font une boîte « ×10 »."),
    ("pn-pass", "Passée", "Une étape du parcours type qui précède une étape atteinte, sans trace : une validation, un hook."),
    ("pn-next", "À venir", "Cercle vide et cadre en pointillés."),
]


def page() -> str:
    states = "".join(f'<li><span class="pn-dot {cls}" aria-hidden="true"></span><b>{name}</b><span>{what}</span></li>'
                     for cls, name, what in STATES)
    return f"""<p class="kw-lead">Le Mod affiche, à droite de la conversation, où en est la session : le workflow Kwa
en cours, brique par brique, les sous-agents qui tournent, et en bas le coût de la session et le remplissage de la
fenêtre de contexte. C'est un mod de Claude Code, séparé du plugin : il lit les événements de la session et
dessine, sans rien écrire dans le contexte du modèle ni bloquer quoi que ce soit.</p>

<div class="pn-grid">
<figure class="pn-shot"><img src="assets/panneau.webp" width="348" height="726" loading="lazy"
  alt="Le Mod pendant une relecture : briques Cadrer, Faire et Prouver fermées, brique Relire ouverte avec un relecteur en cours, carte « 1 sous-agent tourne », puis la carte du coût et du contexte à 21 %.">
<figcaption>Une relecture en cours dans Claude Desktop : la brique Relire est ouverte, le relecteur mouline.</figcaption></figure>

<div class="pn-text">
<h2 class="kw-section-title">Ce qu'il montre</h2>
<ul class="pn-list">
<li><b>Le workflow détecté.</b> La première skill Kwa de la session le désigne : <code>/kwa:debug</code> donne
« Corriger un bug », <code>/kwa:review</code> « Relire », <code>/kwa:commit</code>, <code>/kwa:ship</code> ou
<code>/kwa:deploy</code> « Livrer », <code>/kwa:learn</code> « Capitaliser » ; sinon « Développer une fonctionnalité ».
Ce sont les cinq <a href="board.html">workflows animés</a> du site, avec les mêmes briques et les mêmes étapes.</li>
<li><b>Une brique ouverte à la fois</b>, celle de l'étape en cours. Les autres restent fermées, avec une pastille par
étape. Quand la session entre dans une nouvelle brique, elle se déplie : le cadre grandit, la suite glisse, les étapes
arrivent en cascade.</li>
<li><b>Les sous-agents qui tournent</b>, dans une carte au-dessus du coût : combien en ce moment, le pic en parallèle sur
la session, et pour chacun son type, sa tâche et son temps. Quand tout est revenu, il reste une ligne de bilan.</li>
<li><b>Le coût et le contexte.</b> Le coût de la session en dollars, sa durée, et un anneau pour la fenêtre de contexte :
vert sous 50 %, orange jusqu'à 80 %, rouge au-delà, le moment de penser à <code>/compact</code> ou à
<a href="glossaire.html">passer le relais</a>.</li>
</ul>

<h2 class="kw-section-title">Lire une étape</h2>
<ul class="pn-states">{states}</ul>
</div>
</div>

<h2 class="kw-section-title">Installer</h2>
<p>Le mod est dans la même marketplace que Kwa. Dans Claude Code, une fois la marketplace <code>kwa</code> ajoutée
(<a href="avant-de-commencer.html">Avant de commencer</a>) :</p>
{code(INSTALL)}
<p>Le Mod s'ouvre au démarrage de chaque session. La commande suivante le ferme ou le rouvre :</p>
{code(TOGGLE)}

<h2 class="kw-section-title">Selon l'endroit</h2>
<ul class="pn-list">
<li><b>Claude Desktop et l'application mobile</b> : le dessin animé ci-dessus, en thème clair ou sombre.</li>
<li><b>Terminal</b> : la même information en texte, briques numérotées et étapes en dessous, avec un indicateur qui
tourne. Quand le terminal est trop étroit pour l'afficher à droite, une ligne au-dessus du prompt la remplace : la brique,
l'étape, les sous-agents en cours et le coût.</li>
</ul>

<h2 class="kw-section-title">Ce qu'il ne fait pas</h2>
<ul class="pn-list">
<li>Il ne suit que les skills de Kwa : une commande intégrée comme <code>/review</code> ou une skill de projet n'est pas
une étape.</li>
<li>Les validations par vous, les hooks silencieux et les étapes sautées ne laissent pas de trace : elles deviennent
« passées » dès qu'une étape suivante est atteinte, jamais « faites ».</li>
<li>Le coût affiché est celui que Claude Code calcule pour la session ; sur un abonnement, c'est une estimation, pas
une facture. Pour mesurer ce que coûte Kwa lui-même, voir <a href="alleger.html">Quand alléger</a>.</li>
</ul>
<p class="kd-note">Le code est dans <a href="https://github.com/nesyouyou/kwa/tree/main/mods/kwa-activity"><code>mods/kwa-activity</code></a>,
avec ses tests (<code>claude plugin test mods/kwa-activity</code>).</p>
"""
