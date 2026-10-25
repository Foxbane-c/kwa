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
  budget: { depense: 22.77, plafond: 300 },
  todo: [
    { titre: 'Refaire le panneau', etat: 'en_cours', recit: 'Une liste claire.', qui: 'Claude' },
    { titre: 'Comparer les devis', etat: 'a_faire', recit: 'Côte à côte.', qui: 'Claude', quand: '2026-10-28' },
    { titre: 'Colis échantillon', etat: 'en_attente', recit: 'À l’aéroport.', qui: 'AliExpress', quand: '2026-11-03' },
    { titre: 'Domaine acheté', etat: 'fait', recit: '10,46 $.', qui: 'Toi', quand: '2026-10-25' },
  ],
})

type Corps = Extract<Parameters<typeof test>[1], (...args: never[]) => unknown>
const monter = async ($: Parameters<Corps>[0], on: Parameters<Corps>[1]) => {
  on('fs.read', (_, e) => (/pilotage\.json$/.test(e.path) ? { value: ETAT } : { deny: 'absent' }))
  on('command.register', () => ({ value: { command: 'pilote' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.panes', () => ({ value: [] }))
  on('clock.now', () => ({ value: new Date(2026, 9, 25, 10, 0).getTime() }))
  on('clock.every', () => ({ value: undefined }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
}

test('le panneau montre les quatre sections, les faites repliées, sur chaque surface', async ($, on) => {
  await monter($, on)
  for (const surface of ['desktop', 'mobile'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    const source = (await ui.findAll({ type: 'Svg' })).map(x => String(x.props.source)).join('')
    for (const attendu of ['22,77 €', 'Refaire le panneau', 'Une liste claire.', 'Comparer les devis', 'Colis échantillon', 'J-9'])
      expect(source).toContain(attendu)
    expect(source).not.toContain('Domaine acheté')
    await ui.press({ key: 'sec-fait' })
    const apres = (await ui.findAll({ type: 'Svg' })).map(x => String(x.props.source)).join('')
    expect(apres).toContain('Domaine acheté')
    expect(apres).toContain('class="barre"')
    expect(await ui.find({ type: 'Text', text: /Relu à/ })).toBeTruthy()
    await ui.press({ key: 'sec-fait' })
    await ui.unmount()
  }
  for (const surface of ['terminal', 'vscode'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect(await ui.find({ type: 'Text', text: /Refaire le panneau/ })).toBeTruthy()
    expect(await ui.find({ type: 'Text', text: /Côte à côte/ })).toBeTruthy()
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

test('un sous-agent lancé apparaît en cours avec son nom humain', async ($, on) => {
  on('agent.spawn', () => ({ model: 'sonnet', agentId: 'a1' }))
  await monter($, on)
  await $.agent.spawn({ prompt: 'x', description: 'Comparer les devis reçus', subagentType: 'kwa:explorer', tool_use_id: 't1',
    provider: { plugin: 'engine', tier: 'core' }, parentModel: 'opus', background: false, fork: false })
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const enCours = (await ui.findAll({ type: 'Svg' })).find(x => String(x.props.alt).startsWith('En cours'))
  expect(String(enCours?.props.source)).toContain('Comparer les devis reçus')
  expect(String(enCours?.props.source)).toContain('Explorateur')
  await ui.unmount()
})
