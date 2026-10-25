// Le modèle du panneau : lire l'état du projet, ranger les cartes en sections, compter les jours. Fonctions pures,
// testées sans moteur.
import type { AgentVu, Carte, Etat, Section } from '../types'

const ETAPES = new Set(['fait', 'en_cours', 'a_venir'])
const CARTES = new Set(['en_cours', 'a_faire', 'en_attente', 'fait'])
const DATE = /^\d{4}-\d{2}-\d{2}$/

// Le fichier est écrit à la main ou par Claude : une erreur doit dire quel champ manque, pas casser le panneau.
export function lireEtat(texte: string): Etat {
  let brut: unknown
  try {
    brut = JSON.parse(texte)
  } catch {
    throw new Error('pilotage.json n’est pas du JSON valide')
  }
  const e = brut as Partial<Etat>
  if (typeof e.produit !== 'string') throw new Error('champ « produit » manquant')
  if (!Array.isArray(e.etapes) || e.etapes.some(x => !ETAPES.has(x?.statut))) throw new Error('champ « etapes » invalide')
  if (typeof e.budget?.depense !== 'number' || typeof e.budget?.plafond !== 'number') throw new Error('champ « budget » invalide')
  if (!Array.isArray(e.todo)) throw new Error('champ « todo » manquant')
  const i = e.todo.findIndex(c => typeof c?.titre !== 'string' || typeof c?.recit !== 'string' || typeof c?.qui !== 'string'
    || !CARTES.has(c?.etat) || (c.quand !== undefined && !DATE.test(c.quand)))
  if (i >= 0) throw new Error(`carte n° ${i + 1} invalide (titre, recit, qui, etat en_cours/a_faire/en_attente/fait, quand AAAA-MM-JJ)`)
  return { version: 1, majLe: '', ...e } as Etat
}

// La date du jour en heure locale, au format des échéances (AAAA-MM-JJ)
export function jour(now: number): string {
  const d = new Date(now)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// Jours entre aujourd'hui et une échéance : 0 le jour même, négatif en retard
export function joursAvant(echeance: string, now: number): number {
  const [a, m, j] = echeance.split('-').map(Number) as [number, number, number]
  const [ta, tm, tj] = jour(now).split('-').map(Number) as [number, number, number]
  return Math.round((Date.UTC(a, m - 1, j) - Date.UTC(ta, tm - 1, tj)) / 86400000)
}

// Le nom d'un type d'agent en mots simples, et ce qu'il sait faire
const AGENTS: Record<string, string> = {
  explorer: 'Explorateur · cartographie le code', Explore: 'Explorateur · fouille les fichiers',
  'backend-dev': 'Dév serveur · code l’API', 'frontend-dev': 'Dév interface · code l’écran',
  reviewer: 'Relecteur · vérifie le travail', critique: 'Critique · cherche les failles du plan',
  secu: 'Sécurité · cherche les failles', Plan: 'Architecte · prépare le plan',
  'general-purpose': 'Agent polyvalent', fork: 'Double de Claude · même contexte',
  'web-fetch': 'Lecteur web · lit une page', 'claude-code-guide': 'Guide Claude Code',
  'jarvis-veille': 'Veille · état de l’art',
}
export const nomAgent = (type: string) => AGENTS[type.replace(/^[\w-]+:/, '')] ?? type

const heure = (t: number) => new Date(t).toTimeString().slice(0, 5)

// Une carte vivante par sous-agent en train de travailler : ce que Claude lui a confié, et depuis quand
export function cartesAgents(agents: AgentVu[]): Carte[] {
  return agents.filter(a => a.enCours).map(a => ({
    titre: a.description, etat: 'en_cours', agent: nomAgent(a.type), qui: 'Claude pilote',
    recit: `Claude a confié ce travail à un agent à ${heure(a.debut)} et en vérifie le résultat. `
      + (a.savoir > 0 ? 'L’agent a relu la mémoire du projet avant d’agir.' : 'L’agent n’a pas encore relu la mémoire du projet.'),
  }))
}

export const SECTIONS: { id: Section; titre: string }[] = [
  { id: 'a_faire', titre: 'À faire' },
  { id: 'en_cours', titre: 'En cours' },
  { id: 'en_attente', titre: 'En attente' },
  { id: 'fait', titre: 'Fait' },
]

// Les cartes d'une section, dans l'ordre de lecture : échéance la plus proche d'abord, sans date à la fin ;
// les faites de la plus récente à la plus ancienne
export function ranger(todo: Carte[], section: Section): Carte[] {
  const liste = todo.filter(c => c.etat === section)
  const cle = (c: Carte) => c.quand ?? '9999-99-99'
  return section === 'fait'
    ? liste.sort((a, b) => (b.quand ?? '').localeCompare(a.quand ?? ''))
    : liste.sort((a, b) => cle(a).localeCompare(cle(b)))
}

// Les faites restent repliées, les autres dépliées, sauf choix de Chaabane
export const estPlie = (s: Section, plies: Record<string, boolean>) => plies[s] ?? s === 'fait'

export const euros = (n: number) => `${n.toFixed(2).replace('.', ',')} €`
