# Pièges connus

## Tester un garde par la ligne de commande est refusé par le garde lui-même (2026-10-07)

- **Symptôme** : une commande de test qui cite un motif interdit (par exemple une lecture d'un fichier `.env`)
  est refusée avant d'être exécutée, même quand le motif n'est qu'un argument d'`echo`.
- **Cause** : les gardes (`PreToolUse`) lisent le *texte* de la commande, pas son effet. Un test qui contient le
  motif est donc, pour eux, la commande dangereuse.
- **Correctif** : tester un garde avec un test unitaire qui lui envoie la charge utile JSON (voir `tests/helpers.py`),
  ou construire le motif à l'exécution dans un fichier de test. Ne pas le coller dans une commande interactive.

## Les gardes git jugeaient le projet de la session, pas le dépôt visé (2026-10-12, Kwa 0.2.0)

- **Symptôme** : « git commit sur main refusé » pour un commit dans un autre dépôt pourtant sur une branche de
  travail, depuis une session ouverte dans un projet sur `main` ; même refus avec `git -C <dépôt>`.
- **Cause** : jusqu'à Kwa 0.2.0, `guard-git` lisait la branche du projet de la session (`CLAUDE_PROJECT_DIR`).
- **Correctif** : Kwa 0.2.1 juge le dépôt que vise la commande (`git -C`, ou un `cd` plus tôt dans la ligne). Avant
  la mise à jour : lancer la session dans le dépôt visé. `KWA_ALLOW_MAIN=1` placé devant la commande ne sert à rien,
  le garde lit l'environnement de Claude Code.
