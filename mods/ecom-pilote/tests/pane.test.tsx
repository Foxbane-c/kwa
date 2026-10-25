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
    const source = (await ui.findAll({ type: 'Svg' })).map(x => String(x.props.source)).join('')
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

test('le tableau des tâches suit les agents, la mémoire et le pliage', async ($, on) => {
  const etat = JSON.stringify({ ...JSON.parse(ETAT), journal: [
    { jour: '2026-10-24', titre: 'Réponse à Vicky', etat: 'fait', qui: 'Claude', savoir: true },
  ] })
  on('fs.read', (_, e) => (/pilotage\.json$/.test(e.path) ? { value: etat } : { deny: 'absent' }))
  on('command.register', () => ({ value: { command: 'pilote' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.panes', () => ({ value: [] }))
  on('mcp.call', (_, e) => ({ value: { content: [{ type: 'text', text: e.tool === 'find-tasks' ? TACHES : JSON.stringify({ tasks: [] }) }], isError: false } }))
  on('clock.now', () => ({ value: new Date(2026, 9, 25, 10, 0).getTime() }))
  on('clock.every', () => ({ value: undefined }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('agent.spawn', () => ({ model: 'sonnet', agentId: 'a1' }))
  on('tool.call', () => ({ result: {} }))

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  await $.agent.spawn({ prompt: 'x', description: 'Comparer les devis', subagentType: 'kwa:explorer', tool_use_id: 't1',
    provider: { plugin: 'engine', tier: 'core' }, parentModel: 'opus', background: false, fork: false })
  // les types de $.tool.call sont trop profonds pour tsc sur un nom MCP non déclaré : appel à travers un type simple
  const appeler = $.tool.call as unknown as (i: { tool: string; query: string }) => Promise<unknown>
  await appeler({ tool: 'mcp__basic-memory__search_notes', query: 'devis' })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const svg = async (alt: string) => (await ui.findAll({ type: 'Svg' })).find(x => String(x.props.alt).startsWith(alt))?.props.source
  expect(String(await svg('Tâches : 1 faites'))).toContain('vault consulté 1 fois')
  const auj = String(await svg('Tâches : Aujourd’hui'))
  expect(auj).toContain('Comparer les devis')
  expect(auj).toContain('Explorateur')
  expect(auj).toContain('stroke-dashoffset')
  // hier est replié ; un clic sur son en-tête le déplie
  expect(await svg('Tâches : Hier')).toBeUndefined()
  await ui.press({ key: 'jour-2026-10-24' })
  expect(String(await svg('Tâches : Hier'))).toContain('Réponse à Vicky')
  await ui.unmount()

  const term = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await term.find({ type: 'Text', text: /TÂCHES · 1 faites · 1 en cours/ })).toBeTruthy()
  await term.unmount()
})
