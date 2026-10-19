# suivi-agents

Mod Claude Code : un schéma des tâches et des agents de la session, ancré à droite, et une ligne d'aide sous le prompt (branche, delta git, contexte, coût, quota 5 h, avancement).

- Les tâches finies sont barrées ; la tâche en cours est ouverte et montre les agents lancés pour elle.
- Un clic sur une tâche la plie ou la déplie.
- `/suivi` rouvre le panneau.

## Installer pour toutes les sessions, tous les projets

```
claude plugin marketplace add "C:\Users\USER\programmeInformatique\claude-mods\suivi-agents"
claude plugin install suivi-agents@chaabane-mods --scope user
```

Le plugin est lu directement depuis ce dossier : après une modification, `/reload-plugins` dans la session suffit.

## Tester

```
claude plugin validate .
claude plugin test .
```
