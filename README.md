# Kwa

**Site : https://nesyouyou.github.io/kwa/** (documentation illustrée et trois parcours de formation)

Kit de workflows automatisés pour le dev agentique : mêmes règles, mêmes garde-fous, mêmes skills, partout, sous
Claude Code comme sous Codex.
Kwa se lit **K**it de **W**orkflows **A**utomatisés : développer une fonctionnalité, corriger un bug, relire, livrer,
capitaliser, chacun outillé par des garde-fous, des hooks et des skills.

## Pourquoi ce dépôt

Kwa est avant tout un **support pédagogique**. Il montre, avec de vrais fichiers qui tournent, comment encadrer un agent
de code : règles, garde-fous, skills, mémoire, workflow. Chaque pièce est lisible, testée, et expliquée sur le
site de documentation et dans trois parcours de formation (culture de l'IA générative, context engineering, harness).

- **En français.** Presque tout ce qui existe sur le sujet est en anglais. Les skills, les règles, la documentation et les
  parcours sont ici en français, pour les développeuses et les développeurs que l'anglais freine.
- **Pour partager des bonnes pratiques.** Ce qui est ici vient de l'usage et d'idées reprises à d'autres projets, toujours
  créditées. Si cela sert à d'autres, tant mieux ; les retours et les corrections sont bienvenus.
- **Sans prétendre à plus.** Les garde-fous sont des filets contre la bévue, pas une frontière de sécurité. Les
  documentations officielles des outils font foi. Les parcours n'ont pas encore été éprouvés avec un groupe.

**Parcours d'apprentissage** : `docs/site/parcours.html`, trois parcours qui s'enchaînent. 1) Culture IA générative (modèle, jetons et probabilités, fenêtre de contexte, agent, hallucinations, prompt engineering, risques). 2) Context engineering (session, AGENTS.md et CLAUDE.md, règles, skills, sous-agents, MCP avec Context7 et Playwright, permissions). 3) Harness (de l'histoire du processus de développement à Kwa, avec dix étapes sur un dépôt jetable dont les sorties viennent de l'exécution réelle, et le flux complet d'un développeur aujourd'hui).

**Documentation illustrée** : `docs/site/index.html` (présentation, arborescence, démarrage) et une page par sujet
(carte des skills, workflow d'une demande, terminal, skills, gardes en action, mémoire, méthode, remplacement de
l'existant, limites, crédits), avec une feuille de style propre (polices dans
`docs/site/style/`, avec leur licence). Régénérer avec `python3 docs/site/build.py` : les exemples sont
calculés en exécutant les gardes.

Il faut d'abord un agent de code (Claude Code ou Codex) : voir la page [Avant de commencer](https://nesyouyou.github.io/kwa/avant-de-commencer.html).

## Installer

Kwa est un **plugin** : skills, agent relecteur, garde-fous et mémoire s'installent une fois par machine. Le projet ne
reçoit que sa configuration (politique, bloc d'AGENTS.md, plugin proposé à l'équipe), jamais de script.

**1. Le plugin, une fois par machine**

```bash
# Claude Code (dans une session)
/plugin marketplace add nesyouyou/kwa
/plugin install kwa@kwa

# Codex
codex plugin marketplace add nesyouyou/kwa
codex plugin add kwa@kwa
```

**2. Le projet, une fois par dépôt** : dans une session Claude Code ouverte dans le projet, lancez `/kwa:init`.
La skill montre ce que Kwa détecte, simule, prépare le dépôt après votre accord, complète la politique avec vous et
vérifie (`kwa detect`, `kwa init --dry-run`, `kwa init`, `kwa doctor` : la commande `kwa` vient avec le plugin).

Puis committez ce qu'elle a écrit (`.claude/kwa.policy.json`, `.claude/settings.json`, `AGENTS.md`, `CLAUDE.md`,
`.codex/`) par une branche : l'équipe reçoit la proposition d'installer le plugin en ouvrant le projet. Sous plugin,
les skills se lancent avec `/kwa:commit` (Claude Code). Les hooks ne s'activent que dans un projet qui a une
politique Kwa ; un worktree créé avant le commit de la configuration reprend celle du dépôt principal.

Sous Codex, deux limites viennent de Codex lui-même : la ligne de commande ne charge pas les hooks d'un plugin, donc
`.codex/hooks.json` les lance par `kwa hook`, et la commande `kwa` doit alors être dans le PATH
(`git clone https://github.com/nesyouyou/kwa ~/kwa`, puis `export PATH="$HOME/kwa/bin:$PATH"` dans `~/.zshrc`) ; et
les noms des skills d'un plugin Codex n'ont pas encore été vérifiés en session.

`kwa init` sur un projet déjà installé par copie le migre : fichiers gérés retirés (une retouche locale est mise de
côté dans `.claude/kwa/backup/`), hooks copiés débranchés, mémoire locale conservée.

**Installation par copie (ancienne méthode)** : `kwa install <projet>` copie toujours scripts et skills dans le projet,
pour un usage sans plugin. Les fichiers copiés sont alors à committer, sinon les worktrees n'ont pas les garde-fous.

```bash
kwa status    <projet>                      # version, modules, dérive locale
kwa recommend <projet>                      # skills tierces utiles pour la stack (rien n'est installé)
kwa build-plugin [--check]                  # régénère plugin/ depuis les sources (mainteneurs)
bash tests/run-safety.sh                    # suite hors-ligne
```

## Noyau + modules + politique

| Module | Apporte |
|---|---|
| `core` | gardes secrets / git / suppression / écriture / politique ; règles ; `/kwa:commit`, `/kwa:ship` |
| `craft` | méthode : `/kwa:brainstorm`, `plan`, `execute`, `agents`, `parallel`, `tdd`, `debug`, `verify`, `review`, `review-feedback` + routage des skills au démarrage de session (remplace superpowers) |
| `memory` | journal des sessions et reprise au démarrage, notes et signaux (corrections, « retiens : », refus de garde), invitation unique en fin de session, `/kwa:learn` (docs, politique, skill de projet, mémoire agent, base de connaissance) |
| `issue-flow` | workflow issue → worktree → preuve → PR « Closes #N » → fusion gardée ; `/kwa:start-dev`, gabarits GitHub |
| `verify` | formatage des fichiers nouveaux ; garde Stop opt-in (`KWA_STOP_VERIFY=1`) |
| `deploy` | `/kwa:deploy` : pré-vol, déploiement, vérification, pilotés par `environments` |
| `client-handover` | règle des 4 tests, `kwa-hygiene`, exceptions datées, job CI (jamais déduit : sur demande) |
| `stack-prisma` | migrations append-only, pas de reset / db push |
| `stack-expo` | `/kwa:testflight`, soumission EAS confirmée |
| `stack-scaleway` | déploiement direct confirmé |

Le spécifique d'un projet vit dans `.claude/kwa.policy.json` (créé une fois à partir de la détection, jamais écrasé) :
`bash.deny/ask`, `write.deny`, `write.no_code_on_main`, `verify.commands`, `start.install`, `environments`, `mobile`,
`hygiene`, `memory`. Exemple complet (monorepo web + API + mobile Expo) : `examples/expo-monorepo.policy.json`.

## Garanties

- `AGENTS.md` : seul le bloc `<!-- kwa:begin … -->` est géré, le reste est intact (testé dans `tests/test_agents_md_bytes.py` : fins de ligne CRLF, absence de retour final, espaces en fin de ligne, saut de page, BOM, accents).
  `CLAUDE.md` devient un pointeur `@AGENTS.md`, sans jamais écraser un fichier qui porte ses propres règles.
- `settings.json` : fusion sans doublon, sauvegarde, écriture atomique, JSON invalide laissé intact.
- Retouche locale d'un fichier géré : sauvegardée avant d'être écrasée. Gabarits « seed » : copiés une fois.
- Aucune action git. Les notes locales et sauvegardes sont exclues via `.git/info/exclude`.
- Les gardes sont des filets contre la bévue, pas une frontière de sécurité ; leurs erreurs internes demandent à
  l'humain. Pour une vraie barrière : protection de branche GitHub + `permissions.deny`.

## Claude Code et Codex

Le même plugin sert les deux agents. Sous Claude Code, il apporte skills (`/kwa:commit`), agent relecteur
(`kwa:relecteur`), hooks et la commande `kwa` ; le projet ne reçoit que sa configuration (`kwa init`, ou `/kwa:init`
dans une session). Sous Codex, le plugin apporte les skills ; Codex lit `AGENTS.md`, les hooks dans
`.codex/hooks.json` (lancés par `kwa hook`), les règles de commandes dans `.codex/rules/kwa.rules` et l'agent
relecteur dans `.codex/agents/kwa-relecteur.toml`, écrits par `kwa init`. Les scripts des gardes sont les mêmes ;
seules les différences de Codex sont traitées :

| Différence de Codex | Ce que fait Kwa |
|---|---|
| Ses hooks ne savent pas demander une confirmation (`ask` y passerait) | Les confirmations de Kwa (push, `reset --hard`, `git clean`, suppression de branche, fusion de PR, et les motifs `codex_prompt` de la politique) sont écrites en règles de commandes Codex : Codex les demande lui-même. Ce qu'aucune règle ne couvre (commande composée, cible calculée, écriture d'un garde) devient un refus expliqué |
| Il édite par `apply_patch`, sans chemin de fichier séparé | Les gardes d'écriture et le formatage lisent le patch (fichiers ajoutés, modifiés, supprimés, déplacés) |
| Il ignore `disable-model-invocation` | Les skills à lancer à la main portent `agents/openai.yaml` (`allow_implicit_invocation: false`) |
| Ses filtres sont des expressions régulières, fin de session limitée à 3 s | Pas de filtre `*`, l'écriture couvre `apply_patch`, délai de fin de session ramené à 3 s |
| Une skill se mentionne avec `$` ; les sous-agents se lancent en langage naturel (`worker`, `explorer`) | Le rappel de routage écrit `$kwa:…` sous Codex ; les skills qui délèguent décrivent les deux façons de faire |

Une règle de projet propre à Codex s'ajoute dans la politique, sur une règle `bash.ask` :
`"codex_prompt": [["scw", "container", "container", ["update", "deploy"]]]` (mots de début de commande, une liste
pour plusieurs choix).

À faire une fois dans Codex : approuver le projet, puis valider ses hooks avec `/hooks` (à refaire après chaque
mise à jour de Kwa, car la validation porte sur le contenu des hooks). Ces adaptations sont vérifiées par
`tests/test_codex.py`, avec les charges que Codex documente ; pas encore dans une vraie session Codex.

## Remplacer un outillage maison

`tests/test_policy_example.py` rejoue contre Kwa des cas représentatifs d'un harnais de garde-fous réel (reset de
base, force-push, cibles de production, workflow issue → PR → preuve, migrations, heredocs) avec la politique d'exemple.
`kwa doctor` signale, dans un projet existant, les hooks et skills maison qui font doublon avec Kwa.

## Origine

Kwa assemble des idées de super-board, superpowers, des skills de Matt Pocock et de ponytail (tous MIT), réécrites
et testées : voir `THIRD_PARTY_NOTICES.md`, `credits.json` et `licenses/`. Aucun fichier copié.

## Licence

MIT, voir `LICENSE`. Les idées reprises d'autres projets (MIT également) sont créditées dans `THIRD_PARTY_NOTICES.md`. Les polices Geist et Geist Mono, vendorisées dans `docs/site/style/`, gardent leur licence (SIL OFL), dans `docs/site/style/assets/licenses/`.
