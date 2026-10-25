import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, Timer } from 'claude-code'

import type { AgentVu, Carte, Section, Vue } from '../types'
import { dessinSection, dessinTete, largeur } from './dessin'
import { SECTIONS, cartesAgents, estPlie, euros, jour, joursAvant, lireEtat, ranger } from './pilotage'

// Lecture seule : le mod lit vault/pilotage.json, observe les sous-agents de la session, et dessine la liste des
// tâches. Il n'écrit rien, ni dans le dépôt, ni dans le contexte du modèle.
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
const CHEMIN = 'vault/pilotage.json'
const RELEVE_MS = 60 * 1000

let poll: Timer | null = null
// Par surface, l'instant de la première apparition : la jauge et les traits des tâches faites se dessinent pendant
// INTRO_MS, une seule fois ; un rendu pendant ce temps redonne le même SVG, donc ne coupe pas l'animation
const vus = new Map<string, number>()
const INTRO_MS = 1500

// Relit le fichier ; renvoie false quand le dossier n'a pas de pilotage.json (le mod reste alors silencieux)
async function relire($: EngineInterface): Promise<boolean> {
  let texte: string
  try {
    texte = await $.fs.read(CHEMIN)
  } catch {
    return false
  }
  let next: Vue
  try {
    next = { etat: lireEtat(texte), erreurEtat: null }
  } catch (err) {
    next = { etat: null, erreurEtat: err instanceof Error ? err.message : 'pilotage.json illisible' }
  }
  // une relecture qui ne change rien ne réécrit pas la vue : le schéma n'est pas redessiné
  await update($, vue, prev => (prev && JSON.stringify(prev) === JSON.stringify(next) ? prev : next))
  const maintenant = await $.clock.now()
  await update($, lu, () => maintenant)
  return true
}

async function ouvrir($: EngineInterface) {
  try {
    return await $.ui.open({ id: PANE, title: TITLE, columns: 72 })
  } catch {
    return { isPlaced: false }
  }
}

const basculer = ($: EngineInterface, s: Section, plie: boolean) => () => void update($, plies, p => ({ ...p, [s]: !plie }))
const estPlace = async ($: EngineInterface) => (await $.ui.panes()).some(p => p.id === PANE && p.isPlaced)

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'pilote', description: 'Afficher ou masquer la liste des tâches du projet E-commerce' })
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
      vus.clear()
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
      } else if ((await read($, agents)).some(a => a.id === e.agentId))
        await update($, agents, l => l.map(a => (a.id === e.agentId ? { ...a, savoir: a.savoir + 1 } : a)))
    }
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    if (e.agentId !== undefined && (await read($, agents)).some(a => a.id === e.agentId && a.enCours)) {
      const fin = await $.clock.now()
      await update($, agents, l => l.map(a => (a.id === e.agentId ? { ...a, enCours: false, fin } : a)))
    }
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
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
    const pli = await read($, plies)
    const mem = await read($, memoire)
    const consultations = mem.jour === jour(now) ? mem.n : 0
    const vivants = cartesAgents(await read($, agents))
    const cartes = (id: Section): Carte[] => (id === 'en_cours' ? [...vivants, ...ranger(s.todo, id)] : ranger(s.todo, id))
    const relu = `Relu à ${new Date(await read($, lu)).toTimeString().slice(0, 5)} · état du ${s.majLe}`
    const entete = (titre: string, n: number, plie: boolean) => `${plie ? '▸' : '▾'}  ${titre} · ${n}`

    // Desktop et mobile : des cartes SVG sous des en-têtes cliquables ; une seule colonne plate, sans Box imbriquée
    if (e.surface === 'desktop' || e.surface === 'mobile') {
      const { Svg } = $.ui.resolve(e)
      // la largeur du panneau en cellules de la police de code (~7,8 px) : le dessin la remplit, et l'image
      // est réduite à la place disponible si l'estimation déborde (Svg sans largeur imposée)
      largeur(e.props.bodyColumns * 7.8)
      if (!vus.has(e.surface)) vus.set(e.surface, now)
      const intro = now - vus.get(e.surface)! < INTRO_MS
      const tete = dessinTete(v, consultations, intro)
      const blocs = SECTIONS.flatMap(({ id, titre }) => {
        const liste = cartes(id)
        const plie = estPlie(id, pli)
        const bouton = <Button key={`sec-${id}`} plain dimColor={plie} onPress={basculer($, id, plie)}>{entete(titre, liste.length, plie)}</Button>
        if (plie) return [bouton]
        const d = dessinSection(liste, id, now, intro)
        return [bouton, <Svg key={`svg-${id}`} source={d.source} alt={`${titre} : ${liste.map(c => c.titre).join(', ') || 'rien'}`} />]
      })
      return (
        <Box flexDirection="column" alignItems="center" width="100%">
          <Svg key="tete" source={tete.source} alt={`Pilotage : ${s.produit}, ${euros(s.budget.depense)} dépensés`} />
          {blocs}
          <Text dimColor wrap="truncate">{relu}</Text>
        </Box>
      )
    }

    // Terminal et VS Code : la même liste en texte
    const marque: Record<Section, string> = { en_cours: '●', a_faire: '○', en_attente: '◔', fait: '✓' }
    return (
      <Box flexDirection="column" gap={1} paddingX={1}>
        <Box flexDirection="column">
          <Text bold>{s.produit}</Text>
          <Text dimColor>{`Dépensé ${euros(s.budget.depense)} sur ${euros(s.budget.plafond)} · chef d’orchestre : Claude (mémoire relue ${consultations} fois)`}</Text>
        </Box>
        {SECTIONS.map(({ id, titre }) => {
          const liste = cartes(id)
          const plie = estPlie(id, pli)
          return (
            <Box key={`t-${id}`} flexDirection="column">
              <Button key={`sec-${id}`} plain dimColor={plie} onPress={basculer($, id, plie)}>{entete(titre, liste.length, plie)}</Button>
              {plie ? null : liste.map((c, i) => {
                const n = c.quand && id !== 'fait' ? joursAvant(c.quand, now) : null
                return (
                  <Box key={`${id}-${i}`} flexDirection="column">
                    <Text color={id === 'en_cours' ? 'claude' : n !== null && n < 0 ? 'error' : undefined} dimColor={id === 'fait'} strikethrough={id === 'fait'}>
                      {`${marque[id]} ${c.titre}`}
                    </Text>
                    <Text dimColor wrap="wrap">{`  ${c.recit}`}</Text>
                    <Text dimColor>{`  ${[c.qui, c.agent, c.quand && `${c.quand.slice(8)}/${c.quand.slice(5, 7)}`].filter(Boolean).join(' · ')}`}</Text>
                  </Box>
                )
              })}
            </Box>
          )
        })}
        <Text dimColor>{relu}</Text>
      </Box>
    )
  })
}
