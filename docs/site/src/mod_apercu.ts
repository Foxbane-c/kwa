// Aperçu de la page « Le Mod » (npx tsx docs/site/src/mod_apercu.ts docs/site/assets) : le dessin tel que le Mod le produit sur Desktop (sans chronomètre, carte du contexte).
import { writeFileSync } from 'node:fs'
import { model, svg } from '../../../mods/kwa-activity/hooks/workflow.ts'

const t = 1_000_000
const S = (id: string, kind: string, name: string, brick: string, s: number, e: number | null, task = '') =>
  ({ id, kind, name, task, brick, startedAt: t + s, endedAt: e === null ? null : t + e, isAborted: false })
const steps = [
  S('1', 'skill', '/kwa:debug', 'cadrer', 0, 40000),
  S('2', 'skill', '/kwa:start-dev', 'faire', 41000, 60000),
  S('3', 'skill', '/kwa:tdd', 'prouver', 61000, null),
  S('a1', 'agent', 'Explore', 'prouver', 65000, null, 'appelants de total()'),
]
const m = model(steps as never, t + 90000, '/kwa:debug', { touched: ['cadrer', 'faire', 'prouver'], current: 'prouver' })
const out = svg(m, { usd: 0.42, tokens: 76000, window: 200000, percent: 38 }, 7 * 60000, { live: false, card: 'context' }).source
const dir = process.argv[2]
writeFileSync(`${dir}/mod-apercu-clair.svg`, out.replace('@media (prefers-color-scheme: dark){', '@media not all{'))
writeFileSync(`${dir}/mod-apercu-sombre.svg`, out.replace('@media (prefers-color-scheme: dark){', '@media all{'))
