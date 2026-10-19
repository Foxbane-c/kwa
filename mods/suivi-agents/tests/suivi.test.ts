import { describe, expect, test } from 'claude-code/testing'

import { barre, delta, ligne } from '../hooks/register'

describe('ligne d’aide', () => {
  test('affiche branche, delta git, contexte et coût avec leur delta', async () => {
    const texte = ligne(
      {
        branche: 'develop',
        ajouts: 120,
        suppressions: 30,
        contexte: 45,
        cout: 1.23,
        avant: { contexte: 42, cout: 1.15 },
      },
      [
        { id: '1', sujet: 'A', statut: 'completed', agents: [] },
        { id: '2', sujet: 'B', statut: 'in_progress', agents: [] },
      ],
      [],
    )
    expect(texte).toBe('⎇ develop +120 −30 · ctx 45 % ▲3 · 1,23 $ ▲0,08 · ✓ 1/2')
  })

  test('pas de delta quand rien n’a bougé', async () => {
    expect(delta(10, 10)).toBe('')
    expect(delta(10, undefined)).toBe('')
    expect(delta(8, 10)).toBe('▼2')
  })

  test('barre d’avancement', async () => {
    expect(barre(3, 6, 6)).toBe('▰▰▰▱▱▱')
    expect(barre(0, 0, 4)).toBe('▱▱▱▱')
  })
})

describe('schéma', () => {
  for (const surface of ['terminal', 'desktop'] as const) {
    test(`une tâche finie est barrée, la tâche en cours s’affiche (${surface})`, async ($, on) => {
      on('tool.call', { tool: 'TaskCreate' }, async ($, e) => ({
        result: { task: { id: e.subject === 'Écrire le mod' ? '1' : '2', subject: e.subject } },
      }))
      on('tool.call', { tool: 'TaskUpdate' }, async ($, e) => ({
        result: { success: true, taskId: e.taskId, updatedFields: ['status'] },
      }))

      await $.tool.call({ tool: 'TaskCreate', subject: 'Écrire le mod', description: 'x' })
      await $.tool.call({
        tool: 'TaskCreate',
        subject: 'Tester le mod',
        description: 'y',
        activeForm: 'Test du mod',
      })
      await $.tool.call({ tool: 'TaskUpdate', taskId: '1', status: 'completed' })
      await $.tool.call({ tool: 'TaskUpdate', taskId: '2', status: 'in_progress' })

      const ui = await $.ui.mount({
        plugin: 'suivi-agents',
        surface,
        component: 'Pane',
        requestId: 'suivi-agents',
        props: { title: 'Suivi', bodyColumns: 48 } as never,
      })
      const finie = await ui.find({ type: 'Text', text: 'Écrire le mod' })
      expect(finie?.props.strikethrough).toBe(true)
      expect(await ui.find({ type: 'Text', text: 'Test du mod' })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /1\/2 tâches/ })).toBeDefined()
      await ui.unmount()
    })
  }
})
