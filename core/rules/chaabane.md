# Règles de Chaabane (module `chaabane`)

Ces règles s'appliquent à tous ses projets, sous Claude Code comme sous Codex. Elles complètent le socle Kwa ;
en cas de conflit, le fichier `AGENTS.md` ou `CLAUDE.md` du projet tranche.

## Communication

- Répondre en français, avec les accents corrects dans tout texte destiné à un humain : auditées, conformité,
  critères, référentiel, modérée. Les clés internes (types, colonnes, tokens CSS) restent en ASCII.
- Pas d'emoji sauf demande explicite. Concis, sans remplissage.
- Chaabane est là pour apprendre : à la première mention d'un outil, d'une bibliothèque, d'un service ou d'un
  acronyme technique, ajouter entre parenthèses un mini-rappel de quinze mots au plus. Expliquer le pourquoi,
  pas seulement le quoi. Quand on construit quelque chose, dire à quoi sert chaque brique.

## Code

- TypeScript strict, aucun `any` sauf justifié par un commentaire.
- Pas de `console.log` oublié, pas de commentaire qui répète le code, pas de sur-ingénierie : trois lignes
  répétées valent mieux qu'une mauvaise abstraction ; centraliser à partir de trois usages.
- Préférer modifier un fichier existant à en créer un nouveau.
- Documenter en JSDoc tous les paramètres d'une fonction exportée.
- Validation à la frontière (entrée utilisateur, API externe) avec Zod ; faire confiance aux types à l'intérieur.
- Jamais de secret en dur : variables d'environnement via `.env`, jamais committé.

## Façon de travailler

- Orchestrer plutôt qu'exécuter seul : au-delà de deux fichiers ou d'une dizaine de lignes, déléguer à un
  sous-agent spécialisé (explorer, backend-dev, frontend-dev, reviewer, critique, secu).
- Phase de plan avant la phase d'implémentation, dans cet ordre.
- Toute modification d'interface est vérifiée visuellement dans un navigateur avant d'être annoncée.
- Convoquer `secu` en plus de la relecture dès qu'un changement touche l'authentification, le paiement, les
  secrets, un endpoint public, l'exécution d'un processus ou du contenu non maîtrisé injecté dans un prompt.

## Portes à sens unique (ordre explicite de Chaabane requis)

- Push sur `master` de RGAAudit, migration de base de données sur des données réelles, texte juridique ou public
  publié, prix, marque. Tout le reste est réversible et se décide sans l'attendre.
- `git push` ailleurs est libre ; signaler quand un push déclenche un déploiement.
- `gh workflow run` et `npm publish` restent sur ordre explicite.
