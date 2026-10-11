"""Page « Avant de commencer » : ce qu'il faut sur sa machine, installer un agent de code, récupérer Kwa.

Les commandes d'installation de Claude Code et de Codex viennent de leur documentation officielle (relue le
2026-10-11) ; les liens y renvoient, car elles évoluent. Aucun prix n'est écrit ici : il change trop souvent.
"""
from __future__ import annotations

from parcours import cmd, code

CLAUDE_DOC = "https://code.claude.com/docs/en/setup"
CODEX_DOC = "https://developers.openai.com/codex/cli"
PATH_LINE = "echo 'export PATH=\"$HOME/kwa/bin:$PATH\"' >> ~/.zshrc && source ~/.zshrc"


def page() -> str:
    return f"""<p class="kw-lead bg-lead">Kwa ne remplace pas un agent de code : il l'encadre. Il vous faut donc d'abord un agent,
<strong>Claude Code</strong> ou <strong>Codex</strong>, qui tourne sur votre machine. Comptez une demi-heure pour tout
installer. Si vous n'avez jamais utilisé d'agent, lisez d'abord le <a href="parcours-culture.html">parcours 1</a> :
il ne demande aucune installation.</p>

<ol class="bg-steps">
<li><h2 class="kw-section-title">Ce qu'il vous faut</h2>
<ul class="pc-list">
<li><strong>Un ordinateur</strong> sous macOS 13 ou plus récent, Windows 10 ou 11, ou Linux (Ubuntu 20.04, Debian 10 ou plus récents). Sous Windows, WSL (un Linux intégré) est le plus simple pour la suite.</li>
<li><strong>Un terminal</strong> : vous y taperez quelques commandes. L'agent travaille aussi dans le terminal.</li>
<li><strong>git</strong> et un compte <strong>GitHub</strong> : Kwa organise le travail en branches et en pull requests.</li>
<li><strong>Python 3</strong> : les garde-fous de Kwa sont de petits scripts Python, sans dépendance à installer.</li>
<li><strong>Node.js</strong>, seulement si vous branchez les serveurs MCP vus au parcours 2 (Context7, Playwright).</li>
</ul></li>

<li><h2 class="kw-section-title">Installer un agent de code</h2>
<div class="kd-grid kd-g2 bg-agents">
<div class="kd-card"><h3>Claude Code</h3>
<p>Sous macOS, Linux ou WSL :</p>{cmd("curl -fsSL https://claude.ai/install.sh | bash")}
<p>Vérifier l'installation, puis lancer l'agent dans un projet :</p>{cmd("claude --version")}{cmd("claude")}
<p><strong>Compte</strong> : un abonnement Claude Pro, Max, Team ou Enterprise, ou un compte Console (facturation à l'usage). L'offre gratuite de claude.ai n'inclut pas Claude Code. Au premier lancement, la connexion se fait dans le navigateur.</p>
<p class="kd-note">Windows, Homebrew, autres méthodes : <a href="{CLAUDE_DOC}">documentation d'installation</a>.</p></div>
<div class="kd-card"><h3>Codex</h3>
<p>Sous macOS ou Linux :</p>{cmd("curl -fsSL https://chatgpt.com/codex/install.sh | sh")}
<p>Lancer l'agent dans un projet :</p>{cmd("codex")}
<p><strong>Compte</strong> : au premier lancement, choisissez « Sign in with ChatGPT » ou une autre méthode de connexion proposée. Les offres qui incluent Codex sont listées par OpenAI.</p>
<p class="kd-note">Windows, npm, Homebrew : <a href="{CODEX_DOC}">documentation de Codex</a>.</p></div>
</div>
<p><strong>Combien ça coûte ?</strong> Un abonnement mensuel, ou une facturation au nombre de jetons consommés. Les prix changent souvent : vérifiez-les sur les sites des deux éditeurs avant de choisir.</p></li>

<li><h2 class="kw-section-title">Un premier échange</h2>
<p>Ouvrez un projet que vous connaissez, lancez l'agent, puis posez une question qui ne modifie rien :</p>
{code("Explique-moi comment ce projet est organisé, et comment on lance ses tests.")}
<p>L'agent lit les fichiers et répond. Vous venez de voir la boucle d'un agent : il réfléchit, utilise un outil, lit le résultat. Avant de lui demander de modifier du code, installez Kwa : c'est lui qui posera les garde-fous.</p></li>

<li><h2 class="kw-section-title">Récupérer et installer Kwa</h2>
<p>Kwa se récupère en clonant son dépôt, puis en ajoutant sa commande au chemin du terminal :</p>
{cmd("git clone https://github.com/nesyouyou/kwa ~/kwa")}
{cmd(PATH_LINE)}
<p class="kd-note">Avec bash, remplacez <code>~/.zshrc</code> par <code>~/.bashrc</code>. Sans cette ligne, la commande s'appelle <code>~/kwa/bin/kwa</code>.</p>
<p>Puis, dans votre projet, regardez avant d'écrire :</p>
{cmd("kwa detect ./mon-projet")}{cmd("kwa install ./mon-projet --dry-run")}{cmd("kwa install ./mon-projet")}
<p>Les deux premières commandes n'écrivent rien. La troisième installe Kwa pour Claude Code et pour Codex ; aucune ne fait de commit ni de push. Sous Codex, validez une fois les hooks du projet avec <code>/hooks</code>.</p></li>

<li><h2 class="kw-section-title">Et ensuite</h2>
<p>Suivez les <a href="parcours.html">trois parcours</a> dans l'ordre : comprendre le modèle, lui donner le bon contexte, puis l'encadrer avec Kwa. Un mot vous échappe ? Le <a href="glossaire.html">glossaire</a> traduit chaque terme anglais.</p></li>
</ol>"""
