// Le modèle du panneau : lire l'état du projet, trier les tâches Todoist, compter les jours. Fonctions pures, testées
// sans moteur.
import type { AgentVu, Attente, Entree, Etat, EtatTache, Jour, Ligne, Tache, TacheFaite } from '../types'

const ETAPES = new Set(['fait', 'en_cours', 'a_venir'])
const ATTENTES = new Set(['en_cours', 'repondu', 'recu'])
const PORTES = new Set(['ok', 'ko', 'inconnu'])
const TACHES = new Set(['fait', 'en_cours', 'en_attente'])
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
  if (!Array.isArray(e.attentes) || e.attentes.some(x => !ATTENTES.has(x?.etat) || !/^\d{4}-\d{2}-\d{2}$/.test(x?.echeance ?? '')))
    throw new Error('champ « attentes » invalide (etat ou echeance AAAA-MM-JJ)')
  if (!Array.isArray(e.portes) || e.portes.some(x => !PORTES.has(x?.statut))) throw new Error('champ « portes » invalide')
  if (typeof e.budget?.depense !== 'number' || typeof e.budget?.plafond !== 'number') throw new Error('champ « budget » invalide')
  if (typeof e.todoist?.server !== 'string' || typeof e.todoist?.projectId !== 'string') throw new Error('champ « todoist » invalide')
  if (e.journal !== undefined && (!Array.isArray(e.journal) || e.journal.some(x => typeof x?.titre !== 'string' || !TACHES.has(x?.etat) || !DATE.test(x?.jour ?? ''))))
    throw new Error('champ « journal » invalide (titre, etat fait/en_cours/en_attente, jour AAAA-MM-JJ)')
  return { version: 1, majLe: '', ...e, journal: e.journal ?? [], todoist: { ...e.todoist, labelClaude: e.todoist.labelClaude ?? 'claude' } } as Etat
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

// La réponse de find-completed-tasks : les tâches cochées, rangées au jour local de leur fin
export function lireFaites(contenu: { type: string; text?: string }[]): TacheFaite[] {
  const bloc = contenu.find(c => c.type === 'text' && c.text)?.text
  if (!bloc) return []
  const json = JSON.parse(bloc) as { tasks?: { content: string; completedAt?: string; labels?: string[] }[] }
  return (json.tasks ?? []).filter(t => t.completedAt).map(t => ({ titre: t.content, jour: jour(Date.parse(t.completedAt!)), labels: t.labels ?? [] }))
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

const SEMAINE = ['dim.', 'lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.']
export function libelleJour(j: string, now: number): string {
  if (j === 'sans-date') return 'Sans date'
  const n = joursAvant(j, now)
  if (n === 0) return 'Aujourd’hui'
  if (n === -1) return 'Hier'
  if (n === 1) return 'Demain'
  const [a, m, d] = j.split('-').map(Number) as [number, number, number]
  return `${SEMAINE[new Date(a, m - 1, d).getDay()]} ${j.slice(8)}/${j.slice(5, 7)}`
}

const heure = (t: number) => new Date(t).toTimeString().slice(0, 5)
const ORDRE: Record<EtatTache, number> = { en_cours: 0, en_attente: 1, fait: 2 }

// Le tableau des tâches, jour par jour : le journal de pilotage.json, les sous-agents de la session et Todoist.
// Aujourd'hui d'abord, puis les jours à venir, puis les jours passés du plus récent au plus ancien.
export function jours(journal: Entree[], agents: AgentVu[], ouvertes: Tache[], faites: TacheFaite[], label: string, now: number): Jour[] {
  const auj = jour(now)
  const par = new Map<string, Ligne[]>()
  const mettre = (j: string, l: Ligne) => { const liste = par.get(j) ?? []; liste.push(l); par.set(j, liste) }
  for (const e of journal) mettre(e.jour, {
    titre: e.titre, etat: e.etat, qui: e.qui, agent: e.agent ? nomAgent(e.agent) : null,
    savoir: e.etat === 'en_attente' ? 'sans_objet' : e.savoir ? 'oui' : 'non', heure: null, retard: false,
  })
  for (const a of agents) mettre(jour(a.debut), {
    titre: a.description, etat: a.enCours ? 'en_cours' : 'fait', qui: 'Claude pilote', agent: nomAgent(a.type),
    savoir: a.savoir > 0 ? 'oui' : 'non', heure: a.enCours ? `depuis ${heure(a.debut)}` : `${heure(a.debut)}–${heure(a.fin ?? a.debut)}`, retard: false,
  })
  for (const t of faites) mettre(t.jour, {
    titre: t.titre, etat: 'fait', qui: t.labels.includes(label) ? 'Claude' : 'Toi', agent: null, savoir: 'sans_objet', heure: null, retard: false,
  })
  for (const t of ouvertes) {
    const j = t.echeance === null ? 'sans-date' : t.echeance < auj ? auj : t.echeance
    mettre(j, {
      titre: t.titre.replace(/^Claude\s*:\s*/i, ''), etat: 'en_attente', qui: t.labels.includes(label) ? 'Claude' : 'Toi', agent: null,
      savoir: 'sans_objet', heure: null, retard: t.echeance !== null && t.echeance < auj,
    })
  }
  const rang = (j: string) => (j === auj ? 0 : j === 'sans-date' ? 3 : j > auj ? 1 : 2)
  return [...par.entries()]
    .sort(([a], [b]) => rang(a) - rang(b) || (rang(a) === 2 ? b.localeCompare(a) : a.localeCompare(b)))
    .map(([j, lignes]) => ({
      jour: j, libelle: libelleJour(j, now),
      lignes: lignes.sort((x, y) => ORDRE[x.etat] - ORDRE[y.etat]),
      fait: lignes.filter(l => l.etat === 'fait').length,
      enCours: lignes.filter(l => l.etat === 'en_cours').length,
      enAttente: lignes.filter(l => l.etat === 'en_attente').length,
    }))
}

// Aujourd'hui et tout jour où quelque chose est en cours restent dépliés ; le reste replié, sauf choix de Chaabane
export const estPlie = (j: Jour, plies: Record<string, boolean>, now: number) => plies[j.jour] ?? !(j.jour === jour(now) || j.enCours > 0)

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
