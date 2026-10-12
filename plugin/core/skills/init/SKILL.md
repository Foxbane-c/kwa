---
name: kwa-init
description: Préparer le dépôt courant pour Kwa (politique, bloc d'AGENTS.md, plugin proposé à l'équipe), une fois par dépôt. À lancer quand l'utilisateur dit « /kwa-init », « installe Kwa ici », « prépare ce projet pour Kwa ».
disable-model-invocation: true
---

# Préparer le dépôt pour Kwa

Le plugin apporte skills, gardes et hooks ; le dépôt ne reçoit que sa configuration. La commande `kwa` vient avec le
plugin (son dossier `bin` est dans le PATH de la session) : ne demande pas à l'utilisateur de cloner Kwa ni de modifier
son PATH. Rien n'est commité ni poussé par ces commandes.

1. **Lire sans écrire** : `kwa detect .`. Résume la stack, les modules proposés et la politique déduite, en trois lignes.
2. **Choisir les modules avec l'utilisateur**, une question à la fois et seulement si c'est utile :
   - le dépôt sera-t-il remis à un client ? (`--with client-handover`) ;
   - formater les fichiers nouveaux et vérifier avant de rendre la main ? (`--with verify`).
3. **Simuler** : `kwa init . --dry-run` avec les options choisies. Montre ce qui serait écrit et attends son accord.
4. **Préparer** : `kwa init .` avec les mêmes options.
5. **Compléter la politique** `.claude/kwa.policy.json` avec lui : la commande de test du projet dans `verify.commands`
   (déduite de `package.json`, `pyproject.toml`, `Makefile`… ; la proposer, ne pas l'inventer), et l'installation
   des dépendances dans `start.install` si le projet en a besoin.
6. **Vérifier** : `kwa doctor .`, puis cite le résultat.
7. **Proposer de committer** la configuration (`.claude/kwa.policy.json`, `.claude/settings.json`, `AGENTS.md`,
   `CLAUDE.md`, `.codex/`, gabarits `.github/`) sur une branche, avec `/kwa-commit` puis `/kwa-ship`. Jamais sur
   main ; l'équipe reçoit alors la proposition d'installer le plugin en ouvrant le projet.

Si `kwa` est introuvable (Codex, ou plugin non chargé), dis-le et donne la commande d'installation du plugin ; ne
contourne pas en copiant des fichiers à la main.
