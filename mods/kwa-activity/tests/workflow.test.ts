import { expect, test } from 'claude-code/testing'
import { isOver, model, svg } from '../hooks/workflow'

const step = (id: string, kind: 'skill' | 'agent' | 'garde', name: string, brick: 'cadrer' | 'faire' | 'prouver' | 'relire' | 'livrer' | 'capitaliser', endedAt: number | null) =>
  ({ id, kind, name, task: '', brick, startedAt: 0, endedAt, isAborted: false })

test('le workflow est détecté par la première skill, et les étapes ont leur état', async () => {
  const m = model([step('1', 'skill', '/kwa:debug', 'cadrer', 10), step('2', 'garde', 'guard-write', 'faire', 20), step('3', 'skill', '/kwa:tdd', 'prouver', null)], 30)
  expect(m.title).toBe('Corriger un bug')
  const by = (n: string) => m.rows.find(r => r.name === n)!
  expect(by('/kwa:debug').status).toBe('done')
  expect(by('cause').status).toBe('passed')
  expect(by('guard-write').status).toBe('denied')
  expect(by('/kwa:tdd').status).toBe('run')
  expect(by('/kwa:ship').status).toBe('next')
  expect(model([], 0).title).toBe('Développer une fonctionnalité')
  expect(model([step('1', 'skill', '/kwa:review', 'relire', 5)], 9).title).toBe('Relire')
})

test('le dessin porte le coût, le contexte et une animation sur l\u2019étape en cours', async () => {
  const m = model([step('1', 'skill', '/kwa:tdd', 'prouver', null)], 5000)
  const out = svg(m, { usd: 1.5, tokens: 150000, window: 200000, percent: 75 }, 120000).source
  expect(out).toContain('1,50 $')
  expect(out).toContain('75 %')
  expect(out).toContain('attributeName="r"')    // l'onde de l'étape en cours, pas l'anneau du contexte
  expect(svg(model([step('1', 'skill', '/kwa:tdd', 'prouver', 9)], 10), null, 0).source).not.toContain('attributeName="r"')
})

test('seule la brique en cours est ouverte, et elle ne se déplie que si on le demande', async () => {
  const m = model([step('1', 'skill', '/kwa:debug', 'cadrer', 10), step('2', 'skill', '/kwa:tdd', 'prouver', null)], 30)
  const still = svg(m, null, 0).source
  expect(still).toContain('/kwa:tdd')
  expect(still).toContain('/kwa:verify')        // une étape à venir de la brique ouverte
  expect(still).not.toContain('>/kwa:debug</text>')// brique Cadrer finie : fermée, en pastilles
  expect(still).not.toContain('/kwa:ship')      // brique Livrer à venir : fermée
  expect(still).not.toContain('attributeName="height"')
  expect(svg(m, null, 0, { unfoldAgo: 0 }).source).toContain('attributeName="height"')
  // un rendu en plein dépliage le reprend là où il en est, un rendu après la fin ne le rejoue pas
  expect(svg(m, null, 0, { unfoldAgo: 400 }).source).toContain('begin="-0.40s"')
  expect(svg(m, null, 0, { unfoldAgo: 5000 }).source).not.toContain('attributeName="height"')
})

test('les sous-agents qui tournent en même temps sont comptés et moulinent', async () => {
  const a = (id: string, start: number, end: number | null) => ({ ...step(id, 'agent', 'kwa:reviewer', 'relire', end), startedAt: start, task: 'relire le diff' })
  const m = model([step('1', 'skill', '/kwa:review', 'relire', null), a('a1', 0, null), a('a2', 1, null), a('a3', 2, 5), a('a4', 6, null)], 10)
  expect(m.swarm.running.length).toBe(3)
  expect(m.swarm.done).toBe(1)
  expect(m.swarm.peak).toBe(3)
  const out = svg(m, null, 0).source
  expect(out).toContain('3 sous-agents tournent')
  expect(out).toContain('type="rotate"')
  expect(svg(model([step('1', 'skill', '/kwa:review', 'relire', 4), a('a1', 0, 3)], 9), null, 0).source).toContain('jusqu’à 1 en parallèle'.replace('’', "'"))
})

test('des sous-agents parallèles font une seule boîte, sans faire passer les étapes suivantes', async () => {
  const a = (id: string, name: string, end: number | null) => ({ ...step(id, 'agent', name, 'relire', end), startedAt: 1 })
  const m = model([step('1', 'skill', '/kwa:review', 'relire', null), a('a1', 'kwa:reviewer', null), a('a2', 'Explore', null), a('a3', 'kwa:reviewer', 4)], 10)
  const boxes = m.rows.filter(r => r.kind === 'agent')
  expect(boxes.length).toBe(1)
  expect(boxes[0]!.count).toBe(3)
  expect(boxes[0]!.live).toBe(2)
  expect(boxes[0]!.name).toBe('sous-agents')
  expect(m.rows.find(r => r.name === '/kwa:review-feedback')!.status).toBe('next')
  expect(svg(m, null, 0).source).toContain('sous-agents ×3')
})

test('une étape hors parcours ne fait pas passer les étapes qui la suivent dans l’ordre des briques', async () => {
  // un relecteur pendant un bug : la brique Relire n'existe pas dans ce parcours
  const bug = model([step('1', 'skill', '/kwa:debug', 'cadrer', null), { ...step('a', 'agent', 'kwa:reviewer', 'relire', null) }], 5)
  expect(bug.rows.find(r => r.name === '/kwa:commit')!.status).toBe('next')
  expect(bug.rows.find(r => r.name === '/kwa:learn')!.status).toBe('next')
  expect(bug.rows.findIndex(r => r.kind === 'agent')).toBeLessThan(bug.rows.findIndex(r => r.name === '/kwa:commit'))
  // un commit pendant une fonctionnalité : push, ship et fusion ne sont pas faits pour autant
  const feat = model([step('1', 'skill', '/kwa:brainstorm', 'cadrer', 2), step('2', 'skill', '/kwa:commit', 'livrer', null)], 5)
  expect(feat.rows.find(r => r.name === '/kwa:ship')!.status).toBe('next')
  expect(feat.rows.find(r => r.name === 'fusion')!.status).toBe('next')
})

test('le workflow reste celui de la première skill, même quand elle est sortie de la liste', async () => {
  expect(model([step('9', 'skill', '/kwa:commit', 'livrer', null)], 5, '/kwa:debug').title).toBe('Corriger un bug')
})

test('textes échappés, étape interrompue et taille bornée', async () => {
  const evil = { ...step('a', 'agent', 'kwa:x<y>', 'faire', null), task: '<b>&\u0001' }
  const out = svg(model([step('1', 'skill', '/kwa:execute', 'faire', null), evil], 5), null, 0).source
  expect(out).toContain('&lt;b&gt;&amp;')
  expect(out).not.toContain('<b>')
  expect(out).not.toContain('\u0001')
  const stopped = model([{ ...step('1', 'skill', '/kwa:tdd', 'prouver', 4), isAborted: true }], 5)
  expect(stopped.rows.find(r => r.name === '/kwa:tdd')!.status).toBe('aborted')
  expect(svg(stopped, null, 0).source).toContain('interrompue')
  // des noms distincts pour ne pas tout regrouper : le pire cas réaliste reste sous la limite
  const many = [step('0', 'skill', '/kwa:review', 'relire', null), ...Array.from({ length: 200 }, (_, i) => step(`g${i}`, i % 2 ? 'garde' : 'skill', `/kwa:x${'y'.repeat(i)}`.slice(0, 60), 'relire', 1)),
    ...Array.from({ length: 8 }, (_, i) => ({ ...step(`a${i}`, 'agent', 'kwa:reviewer', 'relire', null), task: 'x'.repeat(200) }))]
  expect(svg(model(many, 9), { usd: 1, tokens: 1, window: 2, percent: 50 }, 0, { unfoldAgo: 0 }).source.length).toBeLessThan(131072)
})

test('un garde qui refuse plusieurs fois fait une seule boîte', async () => {
  const m = model([step('1', 'skill', '/kwa:review', 'relire', null), step('g1', 'garde', 'garde', 'relire', 1), step('g2', 'garde', 'garde', 'relire', 2), step('g3', 'garde', 'garde', 'relire', 3)], 5)
  const boxes = m.rows.filter(r => r.kind === 'garde' && r.brick === 'relire')
  expect(boxes.length).toBe(1)
  expect(boxes[0]!.count).toBe(3)
  expect(svg(m, null, 0).source).toContain('garde ×3')
})

test('une skill relancée qui tourne reste en cours, et les refus regroupés se comptent', async () => {
  const m = model([step('1', 'skill', '/kwa:tdd', 'prouver', 4), { ...step('2', 'skill', '/kwa:tdd', 'prouver', null), startedAt: 5 }], 9)
  const tdd = m.rows.find(r => r.name === '/kwa:tdd')!
  expect(tdd.status).toBe('run')
  expect(tdd.count).toBe(2)
  const g = model([step('1', 'skill', '/kwa:review', 'relire', null), step('g1', 'garde', 'garde', 'relire', 1), step('g2', 'garde', 'garde', 'relire', 2)], 5)
  expect(svg(g, null, 0).source).toContain('2 refus')
  const killed = model([step('1', 'skill', '/kwa:review', 'relire', null), { ...step('a', 'agent', 'kwa:reviewer', 'relire', 3), isAborted: true }], 5)
  expect(killed.rows.find(r => r.kind === 'agent')!.status).toBe('aborted')
})

test('une boîte d’agents reste faite quand un seul est interrompu, et le dit', async () => {
  const a = (id: string, aborted: boolean) => ({ ...step(id, 'agent', 'kwa:reviewer', 'relire', 3), isAborted: aborted })
  const m = model([step('1', 'skill', '/kwa:review', 'relire', null), a('a1', false), a('a2', false), a('a3', true)], 5)
  expect(m.rows.find(r => r.kind === 'agent')!.status).toBe('done')
  expect(svg(m, null, 0).source).toContain('1 interrompu ·')
  const all = model([step('1', 'skill', '/kwa:review', 'relire', null), a('a1', true), a('a2', true)], 5)
  expect(all.rows.find(r => r.kind === 'agent')!.status).toBe('aborted')
})

test('un agent en cours est fini selon la liste du moteur, ou au bout de deux heures pour un agent de workflow', async () => {
  const agent = { ...step('a', 'agent', 'kwa:reviewer', 'relire', null), startedAt: 0 }
  const wf = { ...agent, viaWorkflow: true }
  expect(isOver(agent, 'running', 10)).toBe(false)
  expect(isOver(agent, 'killed', 10)).toBe(true)
  expect(isOver(agent, undefined, 10)).toBe(true)                 // sorti de la liste
  expect(isOver(wf, undefined, 60 * 60 * 1000)).toBe(false)       // agent de workflow : jamais listé
  expect(isOver(wf, undefined, 2 * 60 * 60 * 1000)).toBe(true)    // sans nouvelles depuis deux heures
})
