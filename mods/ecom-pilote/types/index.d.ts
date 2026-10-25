export type StatutEtape = 'fait' | 'en_cours' | 'a_venir'
export type Etape = { id: string; nom: string; statut: StatutEtape }
// en_cours : on attend ; repondu : réponse partielle reçue ; recu : terminé
export type EtatAttente = 'en_cours' | 'repondu' | 'recu'
export type Attente = { quoi: string; qui: string; depuis: string; echeance: string; etat: EtatAttente; preuve: string }
export type Porte = { critere: string; statut: 'ok' | 'ko' | 'inconnu'; valeur: string }
export type Etat = {
  version: number
  majLe: string
  produit: string
  etapes: Etape[]
  budget: { depense: number; plafond: number }
  attentes: Attente[]
  portes: Porte[]
  todoist: { server: string; projectId: string; labelClaude: string }
  // Le journal tenu par Claude : ce qui a été fait, se fait ou attend, jour par jour
  journal: Entree[]
}
export type EtatTache = 'fait' | 'en_cours' | 'en_attente'
// savoir : la mémoire du projet (vault) a été consultée pour cette tâche
export type Entree = { jour: string; titre: string; etat: EtatTache; qui: string; agent?: string; savoir?: boolean; preuve?: string }
// Un sous-agent lancé pendant la session, vu par les hooks agent.spawn, tool.call et turn.complete
export type AgentVu = { id: string; type: string; description: string; debut: number; fin: number | null; enCours: boolean; savoir: number }
// Une tâche Todoist cochée, avec son jour de fin
export type TacheFaite = { titre: string; jour: string; labels: string[] }
// Une ligne du tableau des tâches, toutes sources confondues
export type Ligne = {
  titre: string
  etat: EtatTache
  qui: string
  agent: string | null
  savoir: 'oui' | 'non' | 'sans_objet'
  heure: string | null
  retard: boolean
}
export type Jour = { jour: string; libelle: string; lignes: Ligne[]; fait: number; enCours: number; enAttente: number }
// Une tâche Todoist réduite à ce que le panneau montre
export type Tache = { titre: string; echeance: string | null; labels: string[]; priorite: string }
// Ce que le panneau dessine : l'état lu, les tâches triées, et ce qui a échoué
export type Vue = {
  etat: Etat | null
  erreurEtat: string | null
  aToi: Tache[]
  claude: Tache[]
  ouvertes: Tache[]
  faites: TacheFaite[]
  erreurTodoist: string | null
  lu: number
}

declare module 'claude-code' {
  interface PluginState {
    // lu : l'heure de la dernière relecture, à part pour qu'une relecture sans changement ne redessine pas le schéma
    // agents : les sous-agents de la session ; plies : jour → replié (absent = règle par défaut) ;
    // memoire : consultations du vault par Claude lui-même, le jour donné
    'ecom-pilote': {
      vue: Vue | null; isHidden: boolean; lu: number
      agents: AgentVu[]; plies: Record<string, boolean>; memoire: { jour: string; n: number }
    }
  }
}
