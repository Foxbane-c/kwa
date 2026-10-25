import { expect, test } from 'claude-code/testing'

const PANE = {
  plugin: 'ecom-pilote',
  component: 'Pane',
  requestId: 'ecom-pilote',
  props: { title: 'E-commerce · pilotage', isFocused: false, bodyColumns: 48, placement: 'dock', scroll: { offset: 0, bodyRows: 40 }, view: {} },
} as const

const ETAT = JSON.stringify({
  version: 1, majLe: '2026-10-25', produit: 'Cahier → kit',
  etapes: [{ id: 'valider', nom: 'Valider', statut: 'fait' }, { id: 'echantillon', nom: 'Échantillon', statut: 'en_cours' }],
  budget: { depense: 13.77, plafond: 300 },
  attentes: [{ quoi: 'Colis échantillon', qui: 'AliExpress', depuis: '2026-10-25', echeance: '2026-11-03', etat: 'en_cours', preuve: 'commande 307' }],
  portes: [{ critere: 'Minimum ≤ 100 kits', statut: 'ok', valeur: 'A : 100' }],
  todoist: { server: 'srv', projectId: 'p' },
})
const TACHES = JSON.stringify({ tasks: [
  { content: 'Relever les devis', dueDate: '2026-10-26', labels: ['claude'], priority: 'p2' },
  { content: 'Choisir la marque', labels: [], priority: 'p1' },
] })

test('le panneau montre les cinq sections, sur chaque surface', async ($, on) => {
  // le moteur passe un chemin absolu, avec / ou \ selon le système
  on('fs.read', (_, e) => (/ecom-pilote[\\/]vault[\\/]pilotage\.json$/.test(e.path) ? { value: ETAT } : { deny: 'absent' }))
  on('command.register', () => ({ value: { command: 'pilote' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.panes', () => ({ value: [] }))
  on('mcp.call', () => ({ value: { content: [{ type: 'text', text: TACHES }], isError: false } }))
  on('clock.now', () => ({ value: new Date(2026, 9, 25, 10, 0).getTime() }))
  on('clock.every', () => ({ value: undefined }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })

  // terminal et VS Code : la version texte
  for (const surface of ['terminal', 'vscode'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /À TOI \(1\)/ }))).toBeTruthy()
    expect((await ui.find({ type: 'Text', text: /Choisir la marque/ }))).toBeTruthy()
    expect((await ui.find({ type: 'Text', text: /CLAUDE FAIT \(1\)/ }))).toBeTruthy()
    expect((await ui.find({ type: 'Text', text: /J-9/ }))).toBeTruthy()
    expect((await ui.find({ type: 'Text', text: /Minimum ≤ 100 kits/ }))).toBeTruthy()
    await ui.unmount()
  }
  // desktop et mobile : le schéma SVG, avec l'heure de relecture en texte natif dessous
  for (const surface of ['desktop', 'mobile'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    const svg = await ui.find({ type: 'Svg' })
    const source = String(svg?.props.source ?? '')
    for (const attendu of ['Choisir la marque', 'Relever les devis', 'Colis échantillon', 'J-9', 'Minimum ≤ 100 kits', '13,77 €'])
      expect(source).toContain(attendu)
    expect((await ui.find({ type: 'Text', text: /Relu à/ }))).toBeTruthy()
    await ui.unmount()
  }
})

test('sans pilotage.json, le mod ne s’ouvre pas et /pilote l’explique', async ($, on) => {
  let ouvert = false
  on('command.register', () => ({ value: { command: 'pilote' } }))
  on('ui.open', () => { ouvert = true; return { value: { isPlaced: true } } })
  on('ui.panes', () => ({ value: [] }))
  on('fs.read', () => ({ deny: 'absent' }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  expect(ouvert).toBe(false)
  const r = await $.command.run({ command: 'pilote', args: '', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } })
  expect(r.text).toContain('Pas de vault/pilotage.json')
})
