# ecom-pilote

Mod Claude Code du projet E-commerce : à droite de la conversation, le pilotage du produit en test, dessiné dans la grammaire du Mod Kwa (`kwa-activity`).

- **Parcours** du produit (5 étapes), **budget** du lot (jauge).
- **À toi** : les tâches Todoist de Chaabane (prioritaires ou dues dans la semaine).
- **J'attends** : les attentes externes (devis, colis) avec compte à rebours, barre du temps écoulé, alerte rouge en retard.
- **Claude fait** : les tâches Todoist au label `claude`, dues d'ici 2 jours.
- **Portes avant le lot** : les critères chiffrés de l'audit, anneau « n / total ».

Lecture seule (V1) : le mod lit `vault/pilotage.json` (tenu par Claude) et Todoist (connexion MCP existante), et ne s'ouvre que dans un dossier qui contient ce fichier. `/pilote` affiche ou masque le panneau. Le schéma n'est redessiné que si les données changent ; la jauge et l'anneau ne s'animent qu'à la première apparition.

## Tester

```
claude plugin validate .
claude plugin test .
```
