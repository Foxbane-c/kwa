export type StatutEtape = 'fait' | 'en_cours' | 'a_venir'
export type Etape = { id: string; nom: string; statut: StatutEtape }
export type EtatCarte = 'en_cours' | 'a_faire' | 'en_attente' | 'fait'
// Une carte de la liste : ce qu'on fait, pourquoi, qui la porte. quand : date de fin (fait) ou échéance (le reste)
export type Carte = { titre: string; etat: EtatCarte; recit: string; qui: string; quand?: string; agent?: string }
export type Etat = {
  version: number
  majLe: string
  produit: string
  etapes: Etape[]
  budget: { depense: number; plafond: number }
  todo: Carte[]
}
// Un sous-agent lancé pendant la session, vu par les hooks agent.spawn, tool.call et turn.complete
export type AgentVu = { id: string; type: string; description: string; debut: number; fin: number | null; enCours: boolean; savoir: number }
export type Section = 'en_cours' | 'a_faire' | 'en_attente' | 'fait'
// Ce que le panneau dessine : l'état lu, ou l'erreur qui l'empêche
export type Vue = { etat: Etat | null; erreurEtat: string | null }

declare module 'claude-code' {
  interface PluginState {
    // lu : l'heure de la dernière relecture, à part pour qu'une relecture sans changement ne redessine pas le schéma
    // agents : les sous-agents de la session ; plies : section → repliée (absent = règle par défaut) ;
    // memoire : consultations du vault par Claude lui-même, le jour donné
    'ecom-pilote': {
      vue: Vue | null; isHidden: boolean; lu: number
      agents: AgentVu[]; plies: Record<string, boolean>; memoire: { jour: string; n: number }
    }
  }
}
