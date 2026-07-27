import { describe, it, expect } from 'vitest'
import { useNotification } from './useNotification'

describe('useNotification', () => {
  it('отдаёт именно те методы, которые используют компоненты', () => {
    // регрессия: компоненты деструктурировали несуществующий showNotification
    // и падали с TypeError на каждом уведомлении
    const api = useNotification()
    expect(Object.keys(api).sort()).toEqual(
      ['error', 'info', 'notify', 'snackbar', 'success'].sort())
  })

  it('success/error задают цвет и таймаут', () => {
    const { snackbar, success, error } = useNotification()
    success('Сохранено')
    expect(snackbar.value).toMatchObject({ show: true, text: 'Сохранено', color: 'success', timeout: 3000 })
    error('Упало')
    expect(snackbar.value).toMatchObject({ text: 'Упало', color: 'error', timeout: 5000 })
  })
})
