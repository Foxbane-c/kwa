// Le modèle du panneau : lire l'état du projet, trier les tâches Todoist, compter les jours. Fonctions pures, testées
// sans moteur.
import type { Attente, Etat, Tache } from '../types'

const ETAPES = new Set(['fait', 'en_cours', 'a_venir'])
const ATTENTES = new Set(['en_cours', 'repondu', 'recu'])
const PORTES = new Set(['ok', 'ko', 'inconnu'])

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
  if (!Array.isArray(e.attentes) || e.attentes.some(x => !ATTENTES.has(x?.etat) || !/^\d{4}-\d{2}-\d{2}$/.test(x?.echeance ?? '')))
    throw new Error('champ « attentes » invalide (etat ou echeance AAAA-MM-JJ)')
  if (!Array.isArray(e.portes) || e.portes.some(x => !PORTES.has(x?.statut))) throw new Error('champ « portes » invalide')
  if (typeof e.budget?.depense !== 'number' || typeof e.budget?.plafond !== 'number') throw new Error('champ « budget » invalide')
  if (typeof e.todoist?.server !== 'string' || typeof e.todoist?.projectId !== 'string') throw new Error('champ « todoist » invalide')
  return { version: 1, majLe: '', ...e, todoist: { ...e.todoist, labelClaude: e.todoist.labelClaude ?? 'claude' } } as Etat
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

export function delai(a: Attente, now: number): { texte: string; retard: boolean } {
  if (a.etat === 'recu') return { texte: 'reçu', retard: false }
  const n = joursAvant(a.echeance, now)
  if (n < 0) return { texte: `en retard de ${-n} j`, retard: true }
  if (n === 0) return { texte: 'aujourd’hui', retard: false }
  return { texte: `J-${n} · ${a.echeance.slice(8)}/${a.echeance.slice(5, 7)}`, retard: false }
}

// La réponse de l'outil Todoist find-tasks : un bloc texte qui contient { tasks: [...] }
export function lireTaches(contenu: { type: string; text?: string }[]): Tache[] {
  const bloc = contenu.find(c => c.type === 'text' && c.text)?.text
  if (!bloc) return []
  const json = JSON.parse(bloc) as { tasks?: { content: string; dueDate?: string; labels?: string[]; priority?: string; checked?: boolean }[] }
  return (json.tasks ?? []).filter(t => !t.checked).map(t => ({
    titre: t.content, echeance: t.dueDate ?? null, labels: t.labels ?? [], priorite: t.priority ?? 'p4',
  }))
}

const parEcheance = (a: Tache, b: Tache) => (a.echeance ?? '9999').localeCompare(b.echeance ?? '9999') || a.priorite.localeCompare(b.priorite)

// « Claude fait » : les tâches au label de Claude dues d'ici 2 jours ou en retard ; à défaut, les deux prochaines.
// « À toi » : les autres tâches prioritaires (p1) ou dues dans la semaine, cinq au plus.
export function trier(taches: Tache[], label: string, now: number): { aToi: Tache[]; claude: Tache[] } {
  const proche = (t: Tache, jours: number) => t.echeance !== null && joursAvant(t.echeance, now) <= jours
  const deClaude = taches.filter(t => t.labels.includes(label)).sort(parEcheance)
  const urgent = deClaude.filter(t => proche(t, 2))
  const claude = urgent.length ? urgent : deClaude.filter(t => t.echeance !== null).slice(0, 2)
  const aToi = taches.filter(t => !t.labels.includes(label) && (t.priorite === 'p1' || proche(t, 7))).sort(parEcheance).slice(0, 5)
  return { aToi, claude }
}

export const euros = (n: number) => `${n.toFixed(2).replace('.', ',')} €`
