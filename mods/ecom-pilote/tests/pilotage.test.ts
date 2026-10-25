import { expect, test } from 'claude-code/testing'

import { dessin } from '../hooks/dessin'
import { delai, joursAvant, lireEtat, lireTaches, trier } from '../hooks/pilotage'

const AUJ = new Date(2026, 9, 25, 10, 0).getTime()   // 25/10/2026, 10 h, heure locale

const ETAT = {
  produit: 'Cahier', etapes: [{ id: 'valider', nom: 'Valider', statut: 'fait' }],
  budget: { depense: 13.77, plafond: 300 },
  attentes: [{ quoi: 'Colis', qui: 'AliExpress', depuis: '2026-10-25', echeance: '2026-11-03', etat: 'en_cours', preuve: 'commande' }],
  portes: [{ critere: 'Minimum', statut: 'ok', valeur: '100' }],
  todoist: { server: 'srv', projectId: 'p' },
}

test('les jours se comptent en dates locales, retard compris', () => {
  expect(joursAvant('2026-11-03', AUJ)).toBe(9)
  expect(joursAvant('2026-10-25', AUJ)).toBe(0)
  expect(joursAvant('2026-10-20', AUJ)).toBe(-5)
  const a = ETAT.attentes[0] as Parameters<typeof delai>[0]
  expect(delai(a, AUJ).texte).toBe('J-9 · 03/11')
  expect(delai({ ...a, echeance: '2026-10-20' }, AUJ)).toEqual({ texte: 'en retard de 5 j', retard: true })
  expect(delai({ ...a, etat: 'recu' }, AUJ).texte).toBe('reçu')
})

test('un pilotage.json valide est lu, le label de Claude a une valeur par défaut', () => {
  const e = lireEtat(JSON.stringify(ETAT))
  expect(e.todoist.labelClaude).toBe('claude')
  expect(e.attentes.length).toBe(1)
})

test('un pilotage.json faux dit quel champ est en cause', () => {
  expect(() => lireEtat('{')).toThrow('pas du JSON')
  expect(() => lireEtat(JSON.stringify({ ...ETAT, attentes: [{ ...ETAT.attentes[0], echeance: '3/11' }] }))).toThrow('attentes')
  expect(() => lireEtat(JSON.stringify({ ...ETAT, budget: {} }))).toThrow('budget')
})

test('les tâches Todoist se répartissent entre Claude et Chaabane', () => {
  const taches = lireTaches([{ type: 'text', text: JSON.stringify({ tasks: [
    { content: 'Relever les devis', dueDate: '2026-10-26', labels: ['claude'], priority: 'p2' },
    { content: 'Analyser Kalodata', dueDate: '2026-11-08', labels: ['claude'], priority: 'p2' },
    { content: 'Choisir la marque', labels: [], priority: 'p1' },
    { content: 'Plus tard', dueDate: '2026-12-01', labels: [], priority: 'p3' },
    { content: 'Déjà faite', labels: [], priority: 'p1', checked: true },
  ] }) }])
  expect(taches.length).toBe(4)
  const { aToi, claude } = trier(taches, 'claude', AUJ)
  expect(claude.map(t => t.titre)).toEqual(['Relever les devis'])
  expect(aToi.map(t => t.titre)).toEqual(['Choisir la marque'])
})

test('sans tâche urgente, Claude montre ses deux prochaines', () => {
  const taches = lireTaches([{ type: 'text', text: JSON.stringify({ tasks: [
    { content: 'B', dueDate: '2026-11-10', labels: ['claude'] },
    { content: 'A', dueDate: '2026-11-08', labels: ['claude'] },
    { content: 'C', dueDate: '2026-11-20', labels: ['claude'] },
  ] }) }])
  expect(trier(taches, 'claude', AUJ).claude.map(t => t.titre)).toEqual(['A', 'B'])
})

test('le schéma SVG est bien formé et suit les données', () => {
  const etat = lireEtat(JSON.stringify({ ...ETAT, attentes: [...ETAT.attentes, { quoi: 'Devis <A> & co', qui: 'X', depuis: '2026-10-20', echeance: '2026-10-22', etat: 'en_cours', preuve: '' }] }))
  const d = dessin({ etat, erreurEtat: null, aToi: [], claude: [], erreurTodoist: null, lu: AUJ }, AUJ)
  expect(d.source.startsWith('<svg')).toBe(true)
  expect(d.source).toContain('Devis &lt;A&gt; &amp; co')   // texte échappé
  expect(d.source).toContain('+3 j')                       // attente en retard
  expect(d.source).toContain('Rien ne t’attend')
  expect(d.height).toBeGreaterThan(300)
})

test('la jauge et l’anneau ne s’animent qu’à la première apparition', () => {
  const v = { etat: lireEtat(JSON.stringify(ETAT)), erreurEtat: null, aToi: [], claude: [], erreurTodoist: null, lu: AUJ }
  const entree = dessin(v, AUJ, { intro: true }).source
  const ensuite = dessin(v, AUJ).source
  expect(entree).toContain('attributeName="stroke-dasharray"')
  expect(entree).toContain('attributeName="width"')
  expect(ensuite).not.toContain('attributeName="stroke-dasharray"')
  expect(ensuite).not.toContain('attributeName="width"')
  // les mêmes données redonnent exactement le même SVG : le cadre ne se recharge pas
  expect(dessin(v, AUJ).source).toBe(ensuite)
})
