"""Page « Avant de commencer » : ce qu'il faut sur sa machine, installer un agent de code, récupérer Kwa.

Les commandes d'installation de Claude Code et de Codex viennent de leur documentation officielle (relue le
2026-10-11) ; les liens y renvoient, car elles évoluent. Aucun prix n'est écrit ici : il change trop souvent.
"""
from __future__ import annotations

from parcours import cmd, code

CLAUDE_DOC = "https://code.claude.com/docs/en/setup"
CODEX_DOC = "https://developers.openai.com/codex/cli"


def page() -> str:
    return f"""<p class="kw-lead bg-lead">Kwa ne remplace pas un agent de code : il l'encadre. Il vous faut donc d'abord un agent,
<strong>Claude Code</strong> ou <strong>Codex</strong>, qui tourne sur votre machine. Si vous n'avez jamais utilisé d'agent, lisez d'abord le <a href="parcours-culture.html">parcours 1</a> :
il ne demande aucune installation.</p>

<ol class="bg-steps">
<li><h2 class="kw-section-title">Ce qu'il vous faut</h2>
<ul class="pc-list">
<li><strong>Python 3</strong> : les garde-fous de Kwa sont de petits scripts Python, sans dépendance.</li>
<li><strong>GitHub CLI</strong> (<code>gh</code>), connecté avec <code>gh auth login</code> : Kwa ouvre les issues et les pull requests avec.</li>
<li><strong>Node.js</strong>, seulement pour les serveurs MCP du parcours 2 (Context7, Playwright).</li>
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
</li>

<li><h2 class="kw-section-title">Installer Kwa</h2>
<p>Kwa est un plugin : il s'installe une fois sur votre machine. Dans une session Claude Code :</p>
{code("/plugin marketplace add nesyouyou/kwa")}{code("/plugin install kwa@kwa")}
<p>Sous Codex :</p>
{cmd("codex plugin marketplace add nesyouyou/kwa")}{cmd("codex plugin add kwa@kwa")}
<p>Puis, dans une session ouverte dans votre projet :</p>
{code("/kwa:init")}
<p>La skill montre ce que Kwa détecte, simule, puis prépare le dépôt après votre accord. Elle n'écrit que de la configuration (politique, bloc d'AGENTS.md, plugin proposé à l'équipe) : aucun script, aucun commit. Committez ces fichiers par une branche.</p>
<p class="kd-note">Sous Codex en ligne de commande, les hooks passent par la commande <code>kwa</code>, qui doit alors être dans le PATH : <code>git clone https://github.com/nesyouyou/kwa ~/kwa</code>, puis ajouter <code>export PATH="$HOME/kwa/bin:$PATH"</code> à <code>~/.zshrc</code>. Validez ensuite les hooks du projet avec <code>/hooks</code>.</p></li>

<li><h2 class="kw-section-title">Et ensuite</h2>
<p>Suivez les <a href="parcours.html">trois parcours</a> dans l'ordre : comprendre le modèle, lui donner le bon contexte, puis l'encadrer avec Kwa. Un mot vous échappe ? Le <a href="glossaire.html">glossaire</a> traduit chaque terme anglais.</p></li>
</ol>"""
