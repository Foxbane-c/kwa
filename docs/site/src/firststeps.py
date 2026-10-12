"""Page « Premier pas en 30 minutes » : Kwa sur le dépôt d'exercice nesyouyou/kwa-demo, de l'installation à la PR.

Les refus cités sont ceux des gardes, relevés en les appelant sur une copie du dépôt d'exercice ; un test vérifie
qu'ils figurent toujours dans le code des gardes.
"""
from __future__ import annotations

from parcours import cmd, code

DEMO = "https://github.com/nesyouyou/kwa-demo"
REFUS_WRITE = "Pas de code sur main : ouvrir d'abord l'issue et sa branche (/kwa:start-dev), puis travailler dans le worktree créé."
REFUS_COMMIT = "git commit sur main refusé : travailler sur une branche dédiée et ouvrir une PR"
VERIFY = '"verify": { "commands": ["python3 -m unittest"] }'


def page() -> str:
    return f"""<p class="kw-lead">Un exercice complet sur un petit projet jetable : préparer Kwa, le voir refuser, corriger un
vrai bug de bout en bout, livrer. Il vous faut un agent de code avec le plugin Kwa
(<a href="avant-de-commencer.html">Avant de commencer</a>), et la GitHub CLI connectée.</p>

<ol class="bg-steps">
<li><h2 class="kw-section-title">Créer votre copie du projet</h2>
<p>Le <a href="{DEMO}">dépôt d'exercice</a> est un modèle : chacun travaille sur sa propre copie, où Kwa ouvrira ses issues et ses pull requests.</p>
{cmd("gh repo create kwa-demo --template nesyouyou/kwa-demo --private --clone")}{cmd("cd kwa-demo && python3 -m unittest")}
<p>Quatre tests passent. Pourtant, avec le code <code>PROMO10</code>, un article à 20 € et un à 10 € coûtent 28 € au lieu de 27 €.</p></li>

<li><h2 class="kw-section-title">Préparer le projet pour Kwa</h2>
<p>Lancez <code>claude</code> dans le projet, puis :</p>
{code("/kwa:init")}
<p>La skill montre ce que Kwa détecte : un projet Python avec du code dans <code>src/</code>, qu'il protège sur <code>main</code>. Acceptez le module <code>verify</code> quand elle le propose. Elle simule, puis n'écrit que de la configuration : aucun script n'est copié, les garde-fous viennent du plugin. Pour la commande de test, elle doit vous proposer d'écrire dans <code>.claude/kwa.policy.json</code> :</p>
{code(VERIFY)}
<p>Elle termine par <code>kwa doctor .</code>, qui doit répondre « cible conforme ».</p>
<p>Committez ensuite cette configuration par une branche, comme tout changement, pour que l'équipe la reçoive. Dans un terminal :</p>
{cmd("git switch -c chore/kwa && git add -A && git commit -m 'chore: préparer Kwa'")}
{cmd("git push -u origin chore/kwa && gh pr create --fill && gh pr merge --merge")}
{cmd("git switch main && git pull")}</li>

<li><h2 class="kw-section-title">Voir un garde refuser</h2>
<p>De retour dans la session (ou sous <code>codex</code>, après <code>/hooks</code>), demandez :</p>
{code("Corrige directement src/panier.py sur main, sans branche.")}
<p>L'agent essaie, et le garde l'arrête :</p>
{code("Kwa — " + REFUS_WRITE)}
<p>Même chose pour un <code>git commit</code> sur main : « {REFUS_COMMIT} ». C'est voulu : chaque changement passe par une issue et une branche.</p></li>

<li><h2 class="kw-section-title">Corriger le bug, de bout en bout</h2>
<p>Décrivez le symptôme, pas la solution (sous Codex, une skill s'appelle avec <code>$</code> au lieu de <code>/</code>) :</p>
{code("/kwa:debug Avec PROMO10, un article à 20 € et un à 10 € coûtent 28 € au lieu de 27 €.")}
<p>Ce que vous devez voir, dans cet ordre :</p>
<ul class="pc-list">
<li>l'agent <strong>reproduit</strong> le bug et nomme la cause avant de toucher au code ;</li>
<li>il ouvre une <strong>issue</strong> sur votre copie et travaille dans un <strong>worktree</strong>, sur sa branche (<code>/kwa:start-dev</code>) ;</li>
<li>il écrit d'abord un <strong>test qui échoue</strong>, puis le correctif le plus petit (<code>/kwa:tdd</code>) ;</li>
<li>il lance <code>python3 -m unittest</code> et <strong>cite le résultat</strong> avant de dire « fait » (<code>/kwa:verify</code>).</li>
</ul>
<p>S'il saute une étape, demandez-la par son nom (« passe par /kwa:start-dev ») ; dites-le-lui aussi : c'est aussi ce que la mémoire de Kwa retiendra.</p></li>

<li><h2 class="kw-section-title">Livrer</h2>
{code("/kwa:ship")}
<p>L'agent vous demande de confirmer le push de la branche, puis ouvre une PR qui commence par <code>Closes #</code> et le numéro de l'issue, avec la sortie des tests comme preuve. La fusion reste votre décision : relisez le diff, puis fusionnez sur GitHub.</p></li>

<li><h2 class="kw-section-title">Capitaliser</h2>
{code("/kwa:learn")}
<p>L'agent propose ce qui mérite d'être retenu de la session (un piège, une décision) et l'endroit où l'écrire. Rien n'est écrit sans votre accord.</p></li>
</ol>

<p>Pour aller plus loin, le <a href="parcours-harness.html">parcours 3</a> démonte chaque pièce : gardes, hooks, politique et mémoire.</p>"""
