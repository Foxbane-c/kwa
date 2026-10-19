# Conventions Nuxt 3 / Vue 3 / Tailwind / Prisma (module `stack-nuxt`)

## Vue et Nuxt

- Composition API avec `<script setup lang="ts">` ; pas d'Options API.
- `definePageMeta({ layout, pageTitle })` centralise titre et mise en page : le layout lit `route.meta`,
  les pages enfants ne répètent pas de props.
- Composants Shadcn-vue, organisés en atomic design (`components/shared/` pour les briques réutilisables).

## Tailwind

- Tokens sémantiques uniquement (`text-success`, `bg-muted`), jamais une couleur brute (`text-green-600`).
- Les tokens vivent dans la config Tailwind et le CSS global ; une nouvelle couleur passe par un token.

## Serveur et données

- Services dans `server/modules/` (ou `src/services/`), endpoints typés, entrée validée par Zod.
- Les types Prisma sont la source de vérité : pas de type parallèle qui redécrit une table.
- Migrations Prisma en ajout seulement (voir le module `stack-prisma`).

## Tests

- Vitest pour l'unitaire, Playwright ou un navigateur piloté pour le bout en bout.
- Mocks réalistes : un `User` Prisma complet, pas un `Partial`.

## Accessibilité

- Toute interface destinée à des utilisateurs se relit avec `/kwa-rgaa` avant d'être annoncée comme finie.
