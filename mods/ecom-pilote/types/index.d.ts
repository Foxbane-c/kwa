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
}
// Une tâche Todoist réduite à ce que le panneau montre
export type Tache = { titre: string; echeance: string | null; labels: string[]; priorite: string }
// Ce que le panneau dessine : l'état lu, les tâches triées, et ce qui a échoué
export type Vue = {
  etat: Etat | null
  erreurEtat: string | null
  aToi: Tache[]
  claude: Tache[]
  erreurTodoist: string | null
  lu: number
}

declare module 'claude-code' {
  interface PluginState {
    // lu : l'heure de la dernière relecture, à part pour qu'une relecture sans changement ne redessine pas le schéma
    'ecom-pilote': { vue: Vue | null; isHidden: boolean; lu: number }
  }
}
