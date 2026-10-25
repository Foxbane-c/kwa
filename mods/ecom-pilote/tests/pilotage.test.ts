import { expect, test } from 'claude-code/testing'

import { dessin, dessinJour, dessinTaches } from '../hooks/dessin'
import { delai, estPlie, jours, joursAvant, lireEtat, lireFaites, lireTaches, nomAgent, trier } from '../hooks/pilotage'

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
  const d = dessin({ etat, erreurEtat: null, aToi: [], claude: [], ouvertes: [], faites: [], erreurTodoist: null, lu: AUJ }, AUJ)
  expect(d.source.startsWith('<svg')).toBe(true)
  expect(d.source).toContain('Devis &lt;A&gt; &amp; co')   // texte échappé
  expect(d.source).toContain('+3 j')                       // attente en retard
  expect(d.source).toContain('Rien ne t’attend')
  expect(d.height).toBeGreaterThan(300)
})

test('la jauge et l’anneau ne s’animent qu’à la première apparition', () => {
  const v = { etat: lireEtat(JSON.stringify(ETAT)), erreurEtat: null, aToi: [], claude: [], ouvertes: [], faites: [], erreurTodoist: null, lu: AUJ }
  const entree = dessin(v, AUJ, { intro: true }).source
  const ensuite = dessin(v, AUJ).source
  expect(entree).toContain('attributeName="stroke-dasharray"')
  expect(entree).toContain('attributeName="width"')
  expect(ensuite).not.toContain('attributeName="stroke-dasharray"')
  expect(ensuite).not.toContain('attributeName="width"')
  // les mêmes données redonnent exactement le même SVG : le cadre ne se recharge pas
  expect(dessin(v, AUJ).source).toBe(ensuite)
})

test('le journal est lu, et un journal faux dit lequel', () => {
  expect(lireEtat(JSON.stringify(ETAT)).journal).toEqual([])
  const j = [{ jour: '2026-10-25', titre: 'Domaine acheté', etat: 'fait', qui: 'Toi' }]
  expect(lireEtat(JSON.stringify({ ...ETAT, journal: j })).journal.length).toBe(1)
  expect(() => lireEtat(JSON.stringify({ ...ETAT, journal: [{ ...j[0], etat: 'fini' }] }))).toThrow('journal')
})

test('les tâches se rangent par jour : aujourd’hui, à venir, passés, sans date', () => {
  const ouvertes = lireTaches([{ type: 'text', text: JSON.stringify({ tasks: [
    { content: 'Claude : comparer les devis', dueDate: '2026-10-28', labels: ['claude'] },
    { content: 'Vieille relance', dueDate: '2026-10-20', labels: [] },
    { content: 'Un jour', labels: [] },
  ] }) }])
  const faites = lireFaites([{ type: 'text', text: JSON.stringify({ tasks: [{ content: 'Relier Weave', completedAt: '2026-10-24T14:06:19.698Z', labels: [] }] }) }])
  const agents = [{ id: 'a1', type: 'kwa:explorer', description: 'Cartographier le mod', debut: AUJ - 60000, fin: null, enCours: true, savoir: 1 },
    { id: 'a2', type: 'fork', description: 'Écrire le tableau', debut: AUJ - 3600000, fin: AUJ - 600000, enCours: false, savoir: 0 }]
  const journal = [{ jour: '2026-10-25', titre: 'Domaine acheté', etat: 'fait' as const, qui: 'Toi', savoir: true }]
  const liste = jours(journal, agents, ouvertes, faites, 'claude', AUJ)
  expect(liste.map(j => j.libelle)).toEqual(['Aujourd’hui', 'mer. 28/10', 'Hier', 'Sans date'])
  const auj = liste[0]!
  expect(auj.lignes.map(l => l.etat)).toEqual(['en_cours', 'en_attente', 'fait', 'fait'])
  expect(auj.lignes[0]).toMatchObject({ qui: 'Claude pilote', agent: 'Explorateur · cartographie le code', savoir: 'oui' })
  expect(auj.lignes[1]).toMatchObject({ titre: 'Vieille relance', retard: true, savoir: 'sans_objet' })
  expect(liste[1]!.lignes[0]).toMatchObject({ titre: 'comparer les devis', qui: 'Claude' })
  expect([auj.fait, auj.enCours, auj.enAttente]).toEqual([2, 1, 1])
  expect(nomAgent('inconnu:truc')).toBe('inconnu:truc')
  // aujourd'hui déplié, les autres jours repliés ; le choix de Chaabane l'emporte
  expect(estPlie(auj, {}, AUJ)).toBe(false)
  expect(estPlie(liste[2]!, {}, AUJ)).toBe(true)
  expect(estPlie(liste[2]!, { '2026-10-24': false }, AUJ)).toBe(false)
  // le dessin : compteurs, halo et contour qui tourne pour la tâche en cours, pastilles « savoir »
  const tete = dessinTaches(liste, 3).source
  expect(tete).toContain('vault consulté 3 fois')
  const d = dessinJour(auj).source
  expect(d).toContain('attributeName="stroke-dashoffset"')
  expect(d).toContain('✓ savoir')
  expect(dessinJour(liste[2]!).source).not.toContain('stroke-dashoffset')
  expect(dessinJour(auj).source).toBe(d)
})
