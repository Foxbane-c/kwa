"""Page « Selon l'agent » : la même méthode et la même politique, branchées différemment sous Claude Code, Codex et
GitHub Copilot CLI.

Les refus montrés sont produits au build en appelant le vrai code des gardes (core/hooks/_kwa.py) avec
l'environnement de chaque agent : la page ne peut pas décrire une forme de réponse que le code n'émet pas.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

from parcours import code

HOOKS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "core", "hooks")
REASON = "git commit sur main refusé : travailler sur une branche dédiée et ouvrir une PR"


def refusal(env: dict) -> tuple[str, int, str]:
    """Le refus tel qu'un garde l'émet : sortie standard, code de sortie, sortie d'erreur."""
    script = f"import sys; sys.path.insert(0, {HOOKS!r}); import _kwa; _kwa.decide('deny', {REASON!r})"
    clean = {k: v for k, v in os.environ.items() if k not in ("KWA_AGENT", "COPILOT_PLUGIN_DATA", "KWA_RUNTIME")}
    p = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, cwd=tempfile.mkdtemp(),
                       env={**clean, **env})
    return json.dumps(json.loads(p.stdout), indent=2, ensure_ascii=False), p.returncode, p.stderr.strip()


ROWS = [  # (sujet, Claude Code, Codex, Copilot CLI)
    ("Installer",
     "<code>/plugin marketplace add nesyouyou/kwa</code>, puis <code>/plugin install kwa@kwa</code>",
     "<code>codex plugin marketplace add nesyouyou/kwa</code>, puis <code>codex plugin add kwa@kwa</code> ; la commande <code>kwa</code> doit être dans le PATH",
     "<code>copilot plugin marketplace add nesyouyou/kwa</code>, puis <code>copilot plugin install kwa@kwa</code> : Copilot lit le format de plugin de Claude"),
    ("Consignes du projet",
     "<code>CLAUDE.md</code>, qui pointe vers <code>AGENTS.md</code>",
     "<code>AGENTS.md</code>, de la racine au dossier courant",
     "<code>AGENTS.md</code> (et <code>CLAUDE.md</code>), sous-dossiers compris"),
    ("Appeler une skill",
     "<code>/kwa:commit</code>",
     "<code>$kwa:commit</code>",
     "les skills sont chargées selon la demande ; l'appel direct reste à vérifier"),
    ("Brancher les garde-fous",
     "les hooks du plugin (<code>hooks.claude.json</code>)",
     "<code>.codex/hooks.json</code>, écrit par <code>kwa init</code>, qui appelle <code>kwa hook …</code> : Codex ne charge pas les hooks d'un plugin. À valider dans <code>/hooks</code>",
     "les hooks du plugin, au format Claude : Copilot les traduit (noms d'outils <code>Bash</code>, <code>Edit</code>, <code>Write</code>)"),
    ("Refuser",
     "décision dans <code>hookSpecificOutput</code>, code de sortie 0",
     "même forme que Claude Code",
     "décision aussi au premier niveau, et code de sortie 2, qui vaut refus pour Copilot quel que soit le JSON"),
    ("Demander confirmation",
     "oui",
     "les hooks ne savent pas demander : Kwa laisse une règle de <code>.codex/rules/kwa.rules</code> le faire, sinon il refuse par prudence",
     "oui, dans la CLI"),
    ("Règles de commandes",
     "la politique, lue par les gardes",
     "la politique, traduite aussi en <code>prefix_rule</code> dans <code>.codex/rules/kwa.rules</code>",
     "la politique, lue par les gardes"),
    ("Relecteur en lecture seule",
     "sous-agent <code>kwa:reviewer</code>, outils d'écriture retirés, shell filtré par un hook",
     "agent <code>.codex/agents/kwa-reviewer.toml</code>, écrit par <code>kwa init</code>",
     "à vérifier : le filtre du shell reconnaît le relecteur par le type d'agent, que Copilot ne transmet peut-être pas"),
    ("Mémoire et routage au démarrage",
     "contexte ajouté par le hook de démarrage de session",
     "même mécanisme",
     "même mécanisme ; Copilot lit ce contexte au premier niveau, Kwa l'écrit aux deux endroits"),
    ("Retrouver le projet",
     "<code>CLAUDE_PROJECT_DIR</code>",
     "le dossier courant, puis la racine git",
     "le dossier courant, puis la racine git : Copilot ne fournit pas <code>CLAUDE_PROJECT_DIR</code>"),
]

SOURCES = [
    ("Référence des hooks de Copilot CLI", "https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-hooks-reference"),
    ("Référence des plugins de Copilot CLI", "https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference"),
    ("Instructions lues par chaque surface Copilot", "https://docs.github.com/en/copilot/reference/custom-instructions-support"),
]


def page() -> str:
    claude, claude_code, _ = refusal({})
    copilot, copilot_code, copilot_err = refusal({"COPILOT_PLUGIN_DATA": tempfile.mkdtemp()})
    rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in ROWS)
    sources = "".join(f'<li><a href="{u}">{t}</a></li>' for t, u in SOURCES)
    return f"""<p class="kw-lead">Kwa est une seule méthode et une seule politique par projet
(<code>.claude/kwa.policy.json</code>). Ce qui change d'un agent de code à l'autre, c'est la façon de les brancher :
où l'agent lit ses consignes, comment il lance un garde-fou, et comment il comprend un refus. Les gardes eux-mêmes
sont le même code Python partout.</p>

<h2 class="kw-section-title dg-h">D'un agent à l'autre</h2>
<div class="kd-wrap"><table class="dg-table"><thead><tr><th></th><th>Claude Code</th><th>Codex</th><th>GitHub Copilot CLI</th></tr></thead>
<tbody>{rows}</tbody></table></div>

<h2 class="kw-section-title dg-h">Sous Claude Code</h2>
<p>C'est le cas d'origine. Le plugin apporte les skills, le relecteur et les hooks ; <code>/kwa:init</code> n'écrit dans le
projet que sa politique, le bloc d'<code>AGENTS.md</code> et la proposition d'installer le plugin. Quand une commande
tente un commit sur <code>main</code>, le garde répond ceci, avec le code de sortie {claude_code} :</p>
{code(claude)}

<h2 class="kw-section-title dg-h">Sous Codex</h2>
<p>Codex lit les mêmes skills et le même <code>AGENTS.md</code>, mais il ne charge pas les hooks d'un plugin en ligne de
commande. <code>/kwa:init</code> écrit donc <code>.codex/hooks.json</code>, qui appelle les mêmes gardes par la commande
<code>kwa hook</code>, et traduit la politique en règles de commandes (<code>.codex/rules/kwa.rules</code>). Les hooks d'un
projet ne tournent qu'une fois le projet approuvé et chaque hook validé dans <code>/hooks</code>. Un hook de Codex ne
sait pas demander confirmation : quand une règle de commandes couvre la commande, Kwa laisse Codex demander ; sinon
il refuse, en le disant. Le refus a la même forme que sous Claude Code.</p>

<h2 class="kw-section-title dg-h">Sous GitHub Copilot CLI</h2>
<p>Copilot CLI installe le plugin depuis la même marketplace, parce qu'il sait lire le format de Claude. Il lance ses
hooks en convertissant ses noms d'outils dans ceux de Claude, si bien que les gardes lisent la même entrée. Deux
choses diffèrent, et Kwa s'y adapte quand il reconnaît Copilot (variable <code>COPILOT_PLUGIN_DATA</code>) : Copilot lit
la décision au premier niveau du JSON, et tient le code de sortie 2 pour un refus. Le même commit sur <code>main</code>
donne alors ceci, avec le code de sortie {copilot_code} et, en sortie d'erreur, « {copilot_err} » :</p>
{code(copilot)}
<p>Ce qui reste à confirmer par un essai réel : l'installation depuis la marketplace, l'appel direct d'une skill, et le
relecteur en lecture seule (le filtre du shell s'appuie sur le type d'agent). Le suivi est dans
<a href="https://github.com/nesyouyou/kwa/issues/69">l'issue de compatibilité Copilot</a>. Copilot dans VS Code lit aussi
le format de Claude, mais ses hooks Claude sont à activer (<code>chat.useClaudeHooks</code>) et son harness Local ignore
les filtres par outil.</p>

<h2 class="kw-section-title dg-h">Sources</h2>
<ul>{sources}</ul>
<p class="kd-note">Les deux refus ci-dessus sont produits à la construction du site par le vrai code des gardes,
avec l'environnement de chaque agent.</p>
"""
