import { expect, test } from 'claude-code/testing'

import { dessinSection, dessinTete, lignes } from '../hooks/dessin'
import { cartesAgents, estPlie, lireEtat, ranger } from '../hooks/pilotage'
import type { Carte } from '../types'

const BASE = {
  version: 1, majLe: '2026-10-25', produit: 'Kit', etapes: [{ id: 'v', nom: 'Valider', statut: 'fait' }],
  budget: { depense: 22.77, plafond: 300 },
}
const NOW = new Date(2026, 9, 25, 10, 0).getTime()

test('un pilotage.json faux dit quelle carte est en cause', () => {
  expect(() => lireEtat('{')).toThrow(/JSON/)
  expect(() => lireEtat(JSON.stringify(BASE))).toThrow(/todo/)
  const faux = { ...BASE, todo: [{ titre: 'a', recit: 'b', qui: 'Claude', etat: 'fait' }, { titre: 'c', recit: 'd', qui: 'Toi', etat: 'bientot' }] }
  expect(() => lireEtat(JSON.stringify(faux))).toThrow(/carte n° 2/)
  expect(lireEtat(JSON.stringify({ ...BASE, todo: [] })).todo).toEqual([])
})

test('les cartes se rangent : échéance proche d’abord, faites de la plus récente à la plus ancienne', () => {
  const todo: Carte[] = [
    { titre: 'Sans date', etat: 'a_faire', recit: '', qui: 'Toi' },
    { titre: 'Devis', etat: 'a_faire', recit: '', qui: 'Claude', quand: '2026-10-28' },
    { titre: 'Colis', etat: 'a_faire', recit: '', qui: 'Toi', quand: '2026-11-03' },
    { titre: 'Vieux', etat: 'fait', recit: '', qui: 'Claude', quand: '2026-10-20' },
    { titre: 'Récent', etat: 'fait', recit: '', qui: 'Claude', quand: '2026-10-25' },
  ]
  expect(ranger(todo, 'a_faire').map(c => c.titre)).toEqual(['Devis', 'Colis', 'Sans date'])
  expect(ranger(todo, 'fait').map(c => c.titre)).toEqual(['Récent', 'Vieux'])
  expect(estPlie('fait', {})).toBe(true)
  expect(estPlie('en_cours', {})).toBe(false)
  expect(estPlie('fait', { fait: false })).toBe(false)
})

test('un agent qui travaille devient une carte en cours, avec son nom humain', () => {
  const c = cartesAgents([
    { id: 'a', type: 'kwa:explorer', description: 'Cartographier le mod', debut: NOW, fin: null, enCours: true, savoir: 1 },
    { id: 'b', type: 'fork', description: 'Fini', debut: NOW, fin: NOW, enCours: false, savoir: 0 },
  ])
  expect(c.length).toBe(1)
  expect(c[0]!.agent).toBe('Explorateur · cartographie le code')
  expect(c[0]!.recit).toContain('a relu la mémoire')
})

test('le texte se coupe au mot et finit par … quand il déborde', () => {
  expect(lignes('un deux trois quatre', 9, 3)).toEqual(['un deux', 'trois', 'quatre'])
  const l = lignes('un deux trois quatre cinq six', 9, 2)
  expect(l.length).toBe(2)
  expect(l[1]!.endsWith('…')).toBe(true)
})

test('les cartes : halo pour en cours, trait qui barre les faites, retard en rouge', () => {
  const todo: Carte[] = [
    { titre: 'Panneau', etat: 'en_cours', recit: 'Je refais le panneau.', qui: 'Claude' },
    { titre: 'Domaine acheté', etat: 'fait', recit: 'Cloudflare, 10,46 $.', qui: 'Toi', quand: '2026-10-25' },
    { titre: 'Devis', etat: 'a_faire', recit: 'Comparer.', qui: 'Claude', quand: '2026-10-20' },
  ]
  expect(dessinSection(ranger(todo, 'en_cours'), 'en_cours', NOW, false).source).toContain('stroke-dashoffset')
  const fait = dessinSection(ranger(todo, 'fait'), 'fait', NOW, true).source
  expect(fait).toContain('class="barre"')
  expect(fait).toContain('aujourd’hui')
  expect(dessinSection(ranger(todo, 'a_faire'), 'a_faire', NOW, false).source).toContain('en retard de 5 j')
  expect(dessinSection([], 'en_attente', NOW, false).source).toContain('Rien en attente')
  const tete = dessinTete({ etat: { ...BASE, etapes: [], todo }, erreurEtat: null } as never, 2, false).source
  expect(tete).toContain('22,77 €')
  expect(tete).toContain('mémoire relue 2 fois')
})
