export type Brick = 'cadrer' | 'faire' | 'prouver' | 'relire' | 'livrer' | 'capitaliser'
export type Step = {
  id: string
  kind: 'skill' | 'agent' | 'garde'
  name: string
  task: string
  brick: Brick
  startedAt: number
  endedAt: number | null
  isAborted: boolean
  // lancé par un script de workflow : $.agent.list() ne le liste pas, seule sa fin de tour le clôt
  viaWorkflow?: boolean
}
export type Usage = { usd: number | null; tokens: number | null; window: number; percent: number | null }

declare module 'claude-code' {
  interface PluginState {
    // first : la première skill Kwa de la session, qui dit le workflow ; elle survit à la troncature de steps
    'kwa-activity': { steps: Step[]; first: string | null; usage: Usage | null; frame: number; beat: number; isHidden: boolean }
  }
}
