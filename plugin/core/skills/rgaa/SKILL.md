---
name: kwa-rgaa
description: Relire une interface web (page, composant, formulaire, parcours) au regard du RGAA 4.1, le référentiel français d'accessibilité, et produire une liste de non-conformités avec le critère, la preuve et le correctif. À lancer avant d'annoncer une interface comme finie, sur demande d'audit, ou quand un composant touche le clavier, les formulaires, les images ou les contrastes.
---

# Relecture d'accessibilité RGAA

Le RGAA (Référentiel Général d'Amélioration de l'Accessibilité) est la déclinaison française des WCAG 2.1 :
106 critères répartis en 13 thématiques. Une interface n'est pas « accessible » parce qu'elle a l'air propre ;
elle l'est quand chaque critère applicable est vérifié et que les écarts sont listés. Cette skill ne remplace pas
un audit par une personne formée : elle évite d'annoncer comme fini ce qui exclurait des utilisateurs.

## Quand

- Avant de dire « c'est fait » sur une page, un composant ou un formulaire visible par des utilisateurs.
- Quand un changement touche le clavier, le focus, un formulaire, une image, une couleur, un mouvement.
- Sur demande d'audit d'une page existante.

## Ce qu'on vérifie, thème par thème

Pour chaque point, trois réponses possibles : conforme, non conforme (avec la preuve), non applicable.

| Thème | Vérification concrète |
|---|---|
| 1. Images | Chaque image porteuse d'information a une alternative textuelle pertinente ; une image décorative a `alt=""` ou `aria-hidden`. |
| 2. Cadres | Chaque `iframe` a un `title` qui dit ce qu'elle contient. |
| 3. Couleurs | L'information n'est jamais donnée par la couleur seule. Contraste texte 4,5:1 (3:1 pour le texte large), composants d'interface 3:1. |
| 4. Multimédia | Vidéo : sous-titres et transcription ; audio : transcription. Pas de lecture automatique sans contrôle. |
| 5. Tableaux | Tableau de données : `caption`, en-têtes `th` avec `scope`. Pas de tableau pour la mise en page. |
| 6. Liens | L'intitulé seul (ou avec son contexte) dit où mène le lien. Pas de « cliquez ici ». |
| 7. Scripts | Tout composant scripté est utilisable au clavier et exposé par un rôle, un nom et un état ARIA corrects. Les changements de contexte sont annoncés. |
| 8. Éléments obligatoires | `lang` sur `html`, `title` unique par page, HTML valide, changements de langue signalés. |
| 9. Structure | Un `h1`, hiérarchie de titres sans saut, listes réelles, régions (`main`, `nav`, `header`, `footer`). |
| 10. Présentation | Lisible sans CSS, reflow à 320 px sans défilement horizontal, texte agrandi à 200 % sans perte, focus visible, pas de contenu qui n'apparaît qu'au survol sans équivalent clavier. |
| 11. Formulaires | Chaque champ a une étiquette liée (`label for`, `aria-labelledby`), les champs obligatoires sont indiqués, les erreurs sont nommées, expliquées et reliées au champ, le format attendu est donné, les boutons ont un intitulé explicite. |
| 12. Navigation | Au moins deux moyens de navigation, liens d'évitement, ordre de tabulation logique, pas de piège au clavier. |
| 13. Consultation | Pas de limite de temps non contrôlable, pas de clignotement, documents téléchargeables accessibles ou avec alternative. |

## Comment

1. **Cadrer** : lister les écrans concernés et leurs états (vide, chargement, erreur, succès, modale ouverte).
2. **Automatiser le gros** : lancer un outil d'analyse (axe dans Playwright, ou l'extension du navigateur) sur
   chaque état. Il trouve environ un tiers des écarts : contrastes, attributs manquants, hiérarchie.
3. **Tester au clavier** : parcourir tout l'écran avec Tab, Maj+Tab, Entrée, Espace, flèches, Échap. Noter
   chaque élément inatteignable, chaque focus invisible, chaque piège.
4. **Tester avec un lecteur d'écran** quand c'est possible (NVDA sous Windows, VoiceOver sous macOS) sur les
   formulaires et les composants scriptés : ce qui est annoncé doit suffire à comprendre et agir.
5. **Rédiger** le rapport ci-dessous. Chaque écart cite le critère (ex. 11.1), l'élément, la preuve
   (capture, sélecteur, sortie d'outil) et le correctif proposé. Pas d'écart sans preuve.
6. **Corriger** si c'est dans le périmètre, puis rejouer les étapes 2 et 3 sur ce qui a changé ; passer par
   `/kwa-verify` avant d'annoncer.

## Rapport

```
## Accessibilité RGAA : <écran>

Périmètre : <pages, états, navigateur, outils>
Résultat : <n> non-conformités (<bloquantes> bloquantes), <m> critères non applicables

| Critère | Élément | Constat | Preuve | Correctif |
|---|---|---|---|---|
| 11.1 | champ courriel du formulaire de contact | pas d'étiquette liée | sélecteur `#email`, axe label | `<label for="email">` |

Reste à vérifier par un humain : <lecteur d'écran, zoom, vidéo…>
```

Une non-conformité est bloquante quand elle empêche d'accomplir la tâche (champ sans étiquette, bouton
inatteignable au clavier, piège de focus, contraste illisible) ; les autres sont à corriger avant livraison.

## Ce qu'on ne fait pas

- Annoncer « conforme RGAA » : seule une déclaration d'accessibilité fondée sur un audit complet le peut.
- Ajouter des attributs ARIA pour faire taire un outil : un élément natif bien choisi vaut mieux qu'un `div`
  avec des rôles.
- Retirer l'anneau de focus pour des raisons esthétiques : le styler, jamais le supprimer.
