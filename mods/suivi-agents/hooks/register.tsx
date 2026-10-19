import { atom, read, update } from 'claude-code'
import type { AgentInfo, EngineInterface, Register } from 'claude-code'

import type { Agent, Jauge, Tache, TaskStatus } from '../types'

const PANE = 'suivi-agents'
const taches = atom({ plugin: 'suivi-agents', key: 'taches' } as const, [])
const agents = atom({ plugin: 'suivi-agents', key: 'agents' } as const, [])
const activite = atom({ plugin: 'suivi-agents', key: 'activite' } as const, {})
const bascules = atom({ plugin: 'suivi-agents', key: 'bascules' } as const, [])
const jauge = atom({ plugin: 'suivi-agents', key: 'jauge' } as const, {})

const ACTIFS = new Set(['pending', 'running', 'waiting'])

// ---------- Mise en forme (pure, testée) ----------

const nombre = (n: number, decimales = 0) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: decimales, maximumFractionDigits: decimales })

/** « ▲3 », « ▼1 » ou rien quand le delta est nul ou inconnu. */
export function delta(maintenant?: number, avant?: number, decimales = 0): string {
  if (maintenant === undefined || avant === undefined) return ''
  const d = maintenant - avant
  if (Math.abs(d) < 10 ** -decimales / 2) return ''

  return `${d > 0 ? '▲' : '▼'}${nombre(Math.abs(d), decimales)}`
}

/** La ligne d'aide : branche et delta git, contexte, coût, quota, avancement. */
export function ligne(j: Jauge, liste: readonly Tache[], equipe: readonly Agent[]): string {
  const parts: string[] = []
  if (j.branche) {
    const diff =
      j.ajouts || j.suppressions ? ` +${j.ajouts ?? 0} −${j.suppressions ?? 0}` : ''
    parts.push(`⎇ ${j.branche}${diff}`)
  }
  if (j.contexte !== undefined) {
    parts.push(`ctx ${j.contexte} % ${delta(j.contexte, j.avant?.contexte)}`.trim())
  }
  if (j.cout !== undefined) {
    parts.push(`${nombre(j.cout, 2)} $ ${delta(j.cout, j.avant?.cout, 2)}`.trim())
  }
  if (j.quota !== undefined) parts.push(`5 h ${nombre(j.quota)} %`)
  if (liste.length > 0) {
    const faites = liste.filter(t => t.statut === 'completed').length
    parts.push(`✓ ${faites}/${liste.length}`)
  }
  const actifs = equipe.filter(a => ACTIFS.has(a.statut)).length
  if (actifs > 0) parts.push(`◌ ${actifs} agent${actifs > 1 ? 's' : ''}`)

  return parts.join(' · ')
}

/** Barre d'avancement en blocs : ▰▰▰▱▱▱. */
export function barre(faites: number, total: number, largeur = 12): string {
  if (total === 0) return '▱'.repeat(largeur)
  const pleins = Math.round((faites / total) * largeur)

  return '▰'.repeat(pleins) + '▱'.repeat(largeur - pleins)
}

const MARQUE: Record<TaskStatus, string> = { completed: '✓', in_progress: '▸', pending: '○' }
const COULEUR: Record<TaskStatus, 'success' | 'claude' | 'subtle'> = {
  completed: 'success',
  in_progress: 'claude',
  pending: 'subtle',
}
const MARQUE_AGENT: Record<string, string> = { completed: '✓', failed: '✗', killed: '✗' }

// ---------- Collecte ----------

function versAgent(info: AgentInfo): Agent {
  return { id: info.id, description: info.description, type: info.type, statut: info.status }
}

/** Relit agents et consommation ; n'écrit que ce qui a changé, pour ne pas redessiner pour rien. */
async function rafraichir($: EngineInterface) {
  const liste = (await $.agent.list()).map(versAgent)
  if (JSON.stringify(await read($, agents)) !== JSON.stringify(liste)) {
    await update($, agents, () => liste)
  }

  const usage = await $.session.usage()
  const cinqHeures = usage.rateLimits.find(r => r.kind === 'five_hour')
  const avant = await read($, jauge)
  const apres: Jauge = {
    ...avant,
    contexte: usage.context.percent,
    cout: usage.cost?.usd,
    quota: cinqHeures?.percentUsed,
  }
  if (JSON.stringify(avant) !== JSON.stringify(apres)) await update($, jauge, () => apres)
}

/** Branche et lignes ajoutées / supprimées depuis le dernier commit. */
async function lireGit($: EngineInterface) {
  try {
    const branche = await $.process.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], {
      timeoutMs: 3000,
    })
    if (branche.exitCode !== 0) return
    const stat = await $.process.run(['git', 'diff', '--shortstat', 'HEAD'], { timeoutMs: 5000 })
    const ajouts = Number(/(\d+) insertion/.exec(stat.stdout)?.[1] ?? 0)
    const suppressions = Number(/(\d+) deletion/.exec(stat.stdout)?.[1] ?? 0)
    await update($, jauge, j => ({ ...j, branche: branche.stdout.trim(), ajouts, suppressions }))
  } catch {
    // Pas de dépôt git ici, ou pas de droit de lancer git : la ligne s'en passe.
  }
}

async function nomDuProjet($: EngineInterface): Promise<string> {
  const repo = await $.session.repo()
  const chemin = repo?.root ?? (await $.session.cwd())

  return chemin.split(/[\\/]/).filter(Boolean).pop() ?? 'session'
}

async function ouvrir($: EngineInterface) {
  return $.ui.open({ id: PANE, title: 'Suivi', columns: 48 })
}

// ---------- Hooks ----------

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'suivi',
      description: 'Rouvre le schéma des tâches et des agents',
    })
    const projet = await nomDuProjet($)
    await update($, jauge, j => ({ ...j, projet }))
    void lireGit($)
    $.clock.every(3000, () => rafraichir($))
    void ouvrir($)

    return next(e)
  })

  on('command.run', { command: 'suivi' }, async $ => {
    await ouvrir($)

    return { text: 'Schéma de suivi ouvert.' }
  })

  // Le delta se mesure depuis le début du tour.
  on('prompt.submit', async ($, e, next) => {
    await update($, jauge, j => ({ ...j, avant: { contexte: j.contexte, cout: j.cout } }))

    return next(e)
  }).catch(($, e, next) => next(e))

  on('turn.complete', async ($, e, next) => {
    const fini = await next(e)
    if (!e.agentId) {
      await rafraichir($)
      await lireGit($)
    }

    return fini
  })

  // Dernier outil de chaque boucle : ce qu'on voit « travailler » dans le schéma.
  on('tool.call', async ($, e, next) => {
    const boucle = e.agentId ?? 'main'
    await update($, activite, a => (a[boucle] === e.tool ? a : { ...a, [boucle]: e.tool }))

    return next(e)
  }).catch(($, e, next) => next(e))

  on('tool.call', { tool: 'TaskCreate' }, async ($, e, next) => {
    const ran = await next(e)
    const task = (ran.result as { task?: { id: string; subject: string } } | undefined)?.task
    if (!ran.isError && task) {
      const nouvelle: Tache = {
        id: task.id,
        sujet: task.subject,
        statut: 'pending',
        enCours: e.activeForm,
        agents: [],
      }
      await update($, taches, liste => [...liste.filter(t => t.id !== task.id), nouvelle])
    }

    return ran
  }).catch(($, e, next) => next(e))

  on('tool.call', { tool: 'TaskUpdate' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.isError || 'deny' in ran) return ran

    const statut = e.status
    await update($, taches, liste => {
      if (statut === 'deleted') return liste.filter(t => t.id !== e.taskId)

      return liste.map(t =>
        t.id !== e.taskId
          ? t
          : {
              ...t,
              sujet: e.subject ?? t.sujet,
              enCours: e.activeForm ?? t.enCours,
              statut: statut ?? t.statut,
            },
      )
    })

    return ran
  }).catch(($, e, next) => next(e))

  // Un agent lancé pendant une tâche en cours se range sous elle.
  on('tool.call', { tool: 'Agent' }, async ($, e, next) => {
    const ran = await next(e)
    const agentId = (ran.result as { agentId?: string } | undefined)?.agentId
    if (agentId) {
      await update($, taches, liste => {
        const courante = liste.find(t => t.statut === 'in_progress')

        return liste.map(t =>
          t === courante && !t.agents.includes(agentId)
            ? { ...t, agents: [...t.agents, agentId] }
            : t,
        )
      })
    }
    await rafraichir($)

    return ran
  }).catch(($, e, next) => next(e))

  // ---------- La ligne d'aide sous le prompt ----------
  on('ui.render', { component: 'PromptHint' }, async ($, e, next) => {
    const texte = ligne(await read($, jauge), await read($, taches), await read($, agents))
    if (!texte) return next(e)

    if (e.surface === 'terminal') {
      return next({ ...e, props: { ...e.props, tail: `  ${texte}` } })
    }

    return next({ ...e, props: { ...e.props, hint: texte } })
  })

  // ---------- Le schéma, à droite ----------
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const j = await read($, jauge)
    const liste = await read($, taches)
    const equipe = await read($, agents)
    const outils = await read($, activite)
    const inverses = await read($, bascules)

    const parId = new Map(equipe.map(a => [a.id, a]))
    const ranges = new Set(liste.flatMap(t => t.agents))
    const libres = equipe.filter(a => !ranges.has(a.id))
    const faites = liste.filter(t => t.statut === 'completed').length
    const ouverte = (t: Tache) => (t.statut === 'in_progress') !== inverses.includes(t.id)

    const ligneAgent = (a: Agent, prefixe: string) => (
      <Text>
        <Text dimColor>{prefixe}</Text>
        <Text color={ACTIFS.has(a.statut) ? 'claude' : MARQUE_AGENT[a.statut] === '✗' ? 'error' : 'success'}>
          {MARQUE_AGENT[a.statut] ?? '◌'}{' '}
        </Text>
        <Text>{a.description}</Text>
        <Text dimColor>
          {' '}
          {a.type}
          {ACTIFS.has(a.statut) && outils[a.id] ? ` · ${outils[a.id]}` : ''}
        </Text>
      </Text>
    )

    return (
      <Box flexDirection="column" paddingX={1}>
        <Text weight="bold">
          {j.projet ?? 'Session'}
          <Text dimColor>{j.branche ? `  ⎇ ${j.branche}` : ''}</Text>
        </Text>
        <Text>
          <Text color="claude">{barre(faites, liste.length)}</Text>
          <Text dimColor>
            {'  '}
            {faites}/{liste.length} tâches
          </Text>
        </Text>

        <Box flexDirection="column" marginTop={1}>
          <Text>
            <Text color="claude">◉ </Text>
            <Text weight="semibold">Session principale</Text>
            <Text dimColor>{outils.main ? ` · ${outils.main}` : ''}</Text>
          </Text>

          {liste.length === 0 && <Text dimColor>│  aucune tâche pour l'instant</Text>}

          {liste.map((t, i) => {
            const derniere = i === liste.length - 1 && libres.length === 0
            const branche = derniere ? '└─ ' : '├─ '
            const suite = derniere ? '   ' : '│  '
            const sous = t.agents.map(id => parId.get(id)).filter((a): a is Agent => !!a)
            const pli = sous.length === 0 ? '' : ouverte(t) ? ' ▾' : ` ▸${sous.length}`
            const titre = t.statut === 'in_progress' ? (t.enCours ?? t.sujet) : t.sujet

            return (
              <Box flexDirection="column">
                <Button
                  key={`tache:${t.id}`}
                  plain
                  onPress={() =>
                    update($, bascules, b =>
                      b.includes(t.id) ? b.filter(x => x !== t.id) : [...b, t.id],
                    )
                  }
                >
                  <Text dimColor>{branche}</Text>
                  <Text color={COULEUR[t.statut]}>{MARQUE[t.statut]} </Text>
                  <Text
                    strikethrough={t.statut === 'completed'}
                    dimColor={t.statut === 'completed'}
                    weight={t.statut === 'in_progress' ? 'semibold' : 'regular'}
                  >
                    {titre}
                  </Text>
                  <Text dimColor>{pli}</Text>
                </Button>
                {ouverte(t) &&
                  sous.map((a, k) => ligneAgent(a, `${suite}${k === sous.length - 1 ? '└─ ' : '├─ '}`))}
              </Box>
            )
          })}

          {libres.length > 0 && (
            <Box flexDirection="column">
              <Text dimColor>└─ agents hors tâche</Text>
              {libres.map((a, k) => ligneAgent(a, `   ${k === libres.length - 1 ? '└─ ' : '├─ '}`))}
            </Box>
          )}
        </Box>

        <Box marginTop={1}>
          <Text dimColor>{ligne({ ...j, branche: undefined }, [], [])}</Text>
        </Box>
      </Box>
    )
  })
}
