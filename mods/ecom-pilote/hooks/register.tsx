import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, Timer } from 'claude-code'

import type { Etat, Tache, Vue } from '../types'
import { dessin } from './dessin'
import { delai, euros, lireEtat, lireTaches, trier } from './pilotage'

// V1, lecture seule : le mod lit vault/pilotage.json et les tâches Todoist du projet, et dessine. Il n'écrit rien,
// ni dans le dépôt, ni dans Todoist, ni dans le contexte du modèle.
const vue = atom({ plugin: 'ecom-pilote', key: 'vue' } as const, null)
const isHidden = atom({ plugin: 'ecom-pilote', key: 'isHidden' } as const, false)
const lu = atom({ plugin: 'ecom-pilote', key: 'lu' } as const, 0)

const PANE = 'ecom-pilote'
const TITLE = 'E-commerce · pilotage'
// La session peut être ouverte sur le dossier E-commerce ou sur son parent
const CHEMINS = ['vault/pilotage.json', 'E-commerce/vault/pilotage.json']
const RELEVE_MS = 5 * 60 * 1000

let poll: Timer | null = null
// Par surface, l'instant de la première apparition : la jauge et l'anneau se remplissent pendant INTRO_MS, une seule
// fois ; un rendu pendant ce temps redonne le même SVG, donc ne coupe pas l'animation
const vus = new Map<string, number>()
const INTRO_MS = 1500

async function lireFichier($: EngineInterface): Promise<{ texte: string } | null> {
  for (const p of CHEMINS) {
    try {
      return { texte: await $.fs.read(p) }
    } catch {
      // essayer le chemin suivant
    }
  }
  return null
}

async function lireTodoist($: EngineInterface, etat: Etat): Promise<{ taches: Tache[]; erreur: string | null }> {
  try {
    const r = await $.mcp.call(etat.todoist.server, 'find-tasks', { projectId: etat.todoist.projectId, limit: 100 })
    if (r.isError) return { taches: [], erreur: 'Todoist a refusé la lecture' }
    return { taches: lireTaches(r.content as { type: string; text?: string }[]), erreur: null }
  } catch {
    return { taches: [], erreur: 'Todoist injoignable depuis le mod' }
  }
}

// Relit tout ; renvoie false quand le dossier n'a pas de pilotage.json (le mod reste alors silencieux)
async function relire($: EngineInterface): Promise<boolean> {
  const fichier = await lireFichier($)
  if (!fichier) return false
  const maintenant = await $.clock.now()
  let etat: Etat | null = null
  let erreurEtat: string | null = null
  try {
    etat = lireEtat(fichier.texte)
  } catch (err) {
    erreurEtat = err instanceof Error ? err.message : 'pilotage.json illisible'
  }
  let aToi: Tache[] = [], claude: Tache[] = [], erreurTodoist: string | null = null
  if (etat) {
    const t = await lireTodoist($, etat)
    erreurTodoist = t.erreur
    ;({ aToi, claude } = trier(t.taches, etat.todoist.labelClaude, maintenant))
  }
  const next: Vue = { etat, erreurEtat, aToi, claude, erreurTodoist, lu: maintenant }
  // une relecture qui ne change rien ne réécrit pas la vue : le schéma n'est pas redessiné
  const pareil = (a: Vue | null) => a !== null && JSON.stringify({ ...a, lu: 0 }) === JSON.stringify({ ...next, lu: 0 })
  await update($, vue, prev => (pareil(prev) ? prev : next))
  await update($, lu, () => maintenant)
  return true
}

async function ouvrir($: EngineInterface) {
  try {
    return await $.ui.open({ id: PANE, title: TITLE })
  } catch {
    return { isPlaced: false }
  }
}

const estPlace = async ($: EngineInterface) => (await $.ui.panes()).some(p => p.id === PANE && p.isPlaced)

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'pilote', description: 'Afficher ou masquer le pilotage du projet E-commerce' })
    if (await relire($)) {
      if (!(await read($, isHidden))) await ouvrir($)
      poll ??= $.clock.every(RELEVE_MS, () => void relire($))
    }
    return next(e)
  })

  on('command.run', { command: 'pilote' }, async $ => {
    if (await estPlace($)) {
      await $.ui.close({ id: PANE })
      vus.clear()
      await update($, isHidden, () => true)
      return { text: 'Pilotage masqué. /pilote pour le rouvrir.' }
    }
    if (!(await relire($))) return { text: 'Pas de vault/pilotage.json dans ce dossier : le pilotage sert au projet E-commerce.' }
    await update($, isHidden, () => false)
    poll ??= $.clock.every(RELEVE_MS, () => void relire($))
    const r = await ouvrir($)
    return { text: r.isPlaced ? 'Pilotage ouvert (relu à l’instant).' : 'Pilotage ouvert, en attente de place.' }
  })

  on('ui.close', async ($, e, next) => {
    if (e.id === PANE) {
      vus.clear()   // à la réouverture, la jauge et l'anneau se remplissent de nouveau
      if (e.origin.kind === 'person') await update($, isHidden, () => true)
    }
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const v = await read($, vue)
    if (!v) return <Text dimColor>Lecture du pilotage…</Text>
    if (!v.etat) return (
      <Box flexDirection="column" gap={1}>
        <Text color="error" bold>pilotage.json illisible</Text>
        <Text>{v.erreurEtat ?? ''}</Text>
      </Box>
    )
    const s = v.etat
    const now = await $.clock.now()
    const relu = `Relu à ${new Date(await read($, lu)).toTimeString().slice(0, 5)} · état du ${s.majLe}${v.erreurTodoist ? ` · ${v.erreurTodoist}` : ''}`
    // Desktop et mobile : le schéma SVG, collé en haut ; le terminal et VS Code gardent la version texte
    if (e.surface === 'desktop' || e.surface === 'mobile') {
      const { Svg } = $.ui.resolve(e)
      if (!vus.has(e.surface)) vus.set(e.surface, now)
      const intro = now - vus.get(e.surface)! < INTRO_MS
      const d = dessin(v, now, { intro })
      return (
        <Box flexDirection="column" flexGrow={1} justifyContent="flex-start" alignItems="center" alignSelf="flex-start" width="100%" height="100%">
          <Svg key="pilotage" source={d.source} width={d.width} height={d.height}
            alt={`Pilotage : ${v.aToi.length} pour toi, ${s.attentes.length} attentes, ${s.portes.filter(p => p.statut === 'ok').length} portes sur ${s.portes.length}`} />
          <Text dimColor wrap="truncate">{relu}</Text>
        </Box>
      )
    }
    const marque = (st: string) => (st === 'fait' ? '✓' : st === 'en_cours' ? '●' : '○')
    const titre = (t: string) => <Text bold color="claude">{t}</Text>
    const tache = (t: Tache, i: number) => (
      <Text key={`${t.titre}-${i}`}>
        • {t.titre}{t.echeance ? <Text dimColor>{`  ${t.echeance.slice(8)}/${t.echeance.slice(5, 7)}`}</Text> : ''}
      </Text>
    )
    return (
      <Box flexDirection="column" gap={1} paddingX={1}>
        <Box flexDirection="column">
          <Text bold>{s.produit}</Text>
          <Text>{s.etapes.map((x, i) => `${i + 1} ${x.nom} ${marque(x.statut)}`).join('   ')}</Text>
          <Text dimColor>{`Dépensé ${euros(s.budget.depense)} sur ${euros(s.budget.plafond)} de plafond`}</Text>
        </Box>

        <Box flexDirection="column">
          {titre(`À TOI (${v.aToi.length})`)}
          {v.aToi.length ? v.aToi.map(tache) : <Text dimColor>Rien ne t’attend.</Text>}
        </Box>

        <Box flexDirection="column">
          {titre(`J’ATTENDS (${s.attentes.filter(a => a.etat !== 'recu').length})`)}
          {s.attentes.map((a, i) => {
            const d = delai(a, now)
            return (
              <Box key={`att-${i}`} flexDirection="column">
                <Text>
                  {a.etat === 'repondu' ? '◐' : a.etat === 'recu' ? '✓' : '○'} {a.quoi}
                  <Text color={d.retard ? 'error' : undefined} dimColor={!d.retard}>{`  ${d.texte}`}</Text>
                </Text>
                <Text dimColor>{`   ${a.qui} · ${a.preuve}`}</Text>
              </Box>
            )
          })}
        </Box>

        <Box flexDirection="column">
          {titre(`CLAUDE FAIT (${v.claude.length})`)}
          {v.claude.length ? v.claude.map(tache) : <Text dimColor>Rien de prévu.</Text>}
        </Box>

        <Box flexDirection="column">
          {titre('PORTES AVANT LE LOT')}
          {s.portes.map((p, i) => (
            <Text key={`porte-${i}`} color={p.statut === 'ok' ? 'success' : p.statut === 'ko' ? 'error' : undefined} dimColor={p.statut === 'inconnu'}>
              {`${p.statut === 'ok' ? '✓' : p.statut === 'ko' ? '✗' : '?'} ${p.critere}${p.valeur ? ` (${p.valeur})` : ''}`}
            </Text>
          ))}
        </Box>

        <Text dimColor>{relu}</Text>
      </Box>
    )
  })
}
