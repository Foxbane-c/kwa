import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, Timer } from 'claude-code'

import type { AgentVu, Etat, Jour, Tache, TacheFaite, Vue } from '../types'
import { dessin, dessinJour, dessinTaches } from './dessin'
import { delai, estPlie, euros, jour, jours, lireEtat, lireFaites, lireTaches, trier } from './pilotage'

// Lecture seule : le mod lit vault/pilotage.json et les tâches Todoist du projet, observe les sous-agents de la session,
// et dessine. Il n'écrit rien, ni dans le dépôt, ni dans Todoist, ni dans le contexte du modèle.
const vue = atom({ plugin: 'ecom-pilote', key: 'vue' } as const, null)
const isHidden = atom({ plugin: 'ecom-pilote', key: 'isHidden' } as const, false)
const lu = atom({ plugin: 'ecom-pilote', key: 'lu' } as const, 0)
const agents = atom({ plugin: 'ecom-pilote', key: 'agents' } as const, [] as AgentVu[])
const plies = atom({ plugin: 'ecom-pilote', key: 'plies' } as const, {} as Record<string, boolean>)
const memoire = atom({ plugin: 'ecom-pilote', key: 'memoire' } as const, { jour: '', n: 0 })

// Une lecture du vault (Basic Memory) : ce qui prouve que l'agent a consulté le savoir du projet avant d'agir
const LECTURE_MEMOIRE = /basic-memory__(search_notes|read_note|build_context|recent_activity|search|view_note|fetch|read_content|cat|grep|find|ls|tail)$/
const MAX_AGENTS = 40

const PANE = 'ecom-pilote'
const TITLE = 'E-commerce · pilotage'
// Seulement une session ouverte sur le dossier E-commerce lui-même (installé au niveau de ce projet)
const CHEMINS = ['vault/pilotage.json']
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

async function lireTodoist($: EngineInterface, etat: Etat, now: number): Promise<{ taches: Tache[]; faites: TacheFaite[]; erreur: string | null }> {
  try {
    const r = await $.mcp.call(etat.todoist.server, 'find-tasks', { projectId: etat.todoist.projectId, limit: 100 })
    if (r.isError) return { taches: [], faites: [], erreur: 'Todoist a refusé la lecture' }
    const taches = lireTaches(r.content as { type: string; text?: string }[])
    // les tâches cochées des sept derniers jours ; un échec ici n'efface pas les tâches ouvertes
    let faites: TacheFaite[] = []
    try {
      const f = await $.mcp.call(etat.todoist.server, 'find-completed-tasks',
        { projectId: etat.todoist.projectId, since: jour(now - 6 * 86400000), until: jour(now), limit: 100 })
      if (!f.isError) faites = lireFaites(f.content as { type: string; text?: string }[])
    } catch {
      // tâches faites indisponibles
    }
    return { taches, faites, erreur: null }
  } catch {
    return { taches: [], faites: [], erreur: 'Todoist injoignable depuis le mod' }
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
  let aToi: Tache[] = [], claude: Tache[] = [], ouvertes: Tache[] = [], faites: TacheFaite[] = [], erreurTodoist: string | null = null
  if (etat) {
    const t = await lireTodoist($, etat, maintenant)
    erreurTodoist = t.erreur
    ouvertes = t.taches
    faites = t.faites
    ;({ aToi, claude } = trier(t.taches, etat.todoist.labelClaude, maintenant))
  }
  const next: Vue = { etat, erreurEtat, aToi, claude, ouvertes, faites, erreurTodoist, lu: maintenant }
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

const basculer = ($: EngineInterface, j: Jour, plie: boolean) => () => void update($, plies, p => ({ ...p, [j.jour]: !plie }))
const entete = (j: Jour, plie: boolean) =>
  `${plie ? '▸' : '▾'} ${j.libelle} · ${[j.enCours && `${j.enCours} en cours`, j.enAttente && `${j.enAttente} en attente`, j.fait && `${j.fait} fait${j.fait > 1 ? 'es' : 'e'}`].filter(Boolean).join(' · ')}`
const total = (liste: Jour[], k: 'fait' | 'enCours' | 'enAttente') => liste.reduce((n, j) => n + j[k], 0)

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

  // Les sous-agents : leur lancement (description, type), leurs lectures du vault, leur fin
  on('agent.spawn', async ($, e, next) => {
    const r = await next(e)
    if ('agentId' in r && r.agentId) {
      const id = r.agentId
      const debut = await $.clock.now()
      await update($, agents, l => [...l.filter(a => a.id !== id),
        { id, type: e.subagentType, description: e.description, debut, fin: null, enCours: true, savoir: 0 }].slice(-MAX_AGENTS))
    }
    return r
  })

  on('tool.call', async ($, e, next) => {
    if (LECTURE_MEMOIRE.test(e.tool)) {
      if (e.agentId === undefined) {
        const auj = jour(await $.clock.now())
        await update($, memoire, m => ({ jour: auj, n: m.jour === auj ? m.n + 1 : 1 }))
      } else if ((await read($, agents)).some(a => a.id === e.agentId && a.savoir === 0))
        await update($, agents, l => l.map(a => (a.id === e.agentId ? { ...a, savoir: a.savoir + 1 } : a)))
    }
    return next(e)
  })

  on('turn.start', async ($, e, next) => {
    const r = await next(e)
    if (e.agentId !== undefined && (await read($, agents)).some(a => a.id === e.agentId && !a.enCours))
      await update($, agents, l => l.map(a => (a.id === e.agentId ? { ...a, enCours: true, fin: null } : a)))
    return r
  })

  on('turn.complete', async ($, e, next) => {
    if (e.agentId !== undefined && (await read($, agents)).some(a => a.id === e.agentId && a.enCours)) {
      const fin = await $.clock.now()
      await update($, agents, l => l.map(a => (a.id === e.agentId ? { ...a, enCours: false, fin } : a)))
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
    const liste = jours(s.journal, await read($, agents), v.ouvertes, v.faites, s.todoist.labelClaude, now)
    const pli = await read($, plies)
    const mem = await read($, memoire)
    const consultations = mem.jour === jour(now) ? mem.n : 0
    const { Button } = $.ui.resolve(e)
    const relu = `Relu à ${new Date(await read($, lu)).toTimeString().slice(0, 5)} · état du ${s.majLe}${v.erreurTodoist ? ` · ${v.erreurTodoist}` : ''}`
    // Desktop et mobile : le schéma SVG, collé en haut ; le terminal et VS Code gardent la version texte
    if (e.surface === 'desktop' || e.surface === 'mobile') {
      const { Svg } = $.ui.resolve(e)
      if (!vus.has(e.surface)) vus.set(e.surface, now)
      const intro = now - vus.get(e.surface)! < INTRO_MS
      const tete = dessin(v, now, { intro, partie: 'tete' })
      const suite = dessin(v, now, { intro, partie: 'suite' })
      const t = dessinTaches(liste, consultations)
      return (
        <Box flexDirection="column" flexGrow={1} justifyContent="flex-start" alignItems="center" alignSelf="flex-start" width="100%" height="100%">
          <Svg key="tete" source={tete.source} width={tete.width} height={tete.height} alt={`Pilotage : ${s.produit}`} />
          <Svg key="taches" source={t.source} width={t.width} height={t.height}
            alt={`Tâches : ${total(liste, 'fait')} faites, ${total(liste, 'enCours')} en cours, ${total(liste, 'enAttente')} en attente`} />
          {liste.map(j => {
            const plie = estPlie(j, pli, now)
            const d = plie ? null : dessinJour(j)
            return (
              <Box key={`j-${j.jour}`} flexDirection="column" alignItems="flex-start" width={360}>
                <Button key={`jour-${j.jour}`} plain dimColor={plie} onPress={basculer($, j, plie)}>{entete(j, plie)}</Button>
                {d ? <Svg key={`svg-${j.jour}`} source={d.source} width={d.width} height={d.height} alt={`Tâches : ${j.libelle}`} /> : null}
              </Box>
            )
          })}
          <Svg key="suite" source={suite.source} width={suite.width} height={suite.height}
            alt={`${v.aToi.length} pour toi, ${s.attentes.length} attentes, ${s.portes.filter(p => p.statut === 'ok').length} portes sur ${s.portes.length}`} />
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
          {titre(`TÂCHES · ${total(liste, 'fait')} faites · ${total(liste, 'enCours')} en cours · ${total(liste, 'enAttente')} en attente`)}
          <Text dimColor>{`Chef d’orchestre : Claude · vault consulté ${consultations} fois aujourd’hui`}</Text>
          {liste.map(j => {
            const plie = estPlie(j, pli, now)
            return (
              <Box key={`j-${j.jour}`} flexDirection="column">
                <Button key={`jour-${j.jour}`} plain dimColor={plie} onPress={basculer($, j, plie)}>{entete(j, plie)}</Button>
                {plie ? null : j.lignes.map((l, i) => (
                  <Text key={`${j.jour}-${i}`} color={l.etat === 'en_cours' ? 'claude' : l.retard ? 'error' : undefined} dimColor={l.etat === 'fait'}>
                    {`  ${l.etat === 'fait' ? '✓' : l.etat === 'en_cours' ? '●' : '○'} ${l.titre} — ${[l.qui, l.agent, l.heure].filter(Boolean).join(' · ')}${l.savoir === 'oui' ? ' · ✓ savoir' : l.savoir === 'non' ? ' · ? savoir' : ''}`}
                  </Text>
                ))}
              </Box>
            )
          })}
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
