export type TaskStatus = 'pending' | 'in_progress' | 'completed'

/** Une tâche de la liste (TaskCreate / TaskUpdate), et les agents lancés pendant qu'elle était en cours. */
export type Tache = {
  id: string
  sujet: string
  statut: TaskStatus
  enCours?: string
  agents: string[]
}

/** Un agent de la session, tel que `$.agent.list()` le décrit. */
export type Agent = {
  id: string
  description: string
  type: string
  statut: string
}

/** Les chiffres de la ligne d'aide, avec ceux du tour précédent pour calculer les deltas. */
export type Jauge = {
  projet?: string
  branche?: string
  ajouts?: number
  suppressions?: number
  contexte?: number
  cout?: number
  quota?: number
  /** Valeurs à la fin du tour précédent. */
  avant?: { contexte?: number; cout?: number }
}

declare module 'claude-code' {
  interface PluginState {
    'suivi-agents': {
      taches: Tache[]
      agents: Agent[]
      /** Dernier outil appelé par boucle : 'main' pour la session, sinon l'id de l'agent. */
      activite: Record<string, string>
      /** Tâches dont on a inversé le pli par défaut (ouvert si en cours, fermé sinon). */
      bascules: string[]
      jauge: Jauge
    }
  }
}
