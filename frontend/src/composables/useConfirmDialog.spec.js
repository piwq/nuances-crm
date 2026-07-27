import { describe, it, expect, beforeEach } from 'vitest'
import { useConfirmDialog } from './useConfirmDialog'

describe('useConfirmDialog', () => {
  let dlg

  beforeEach(() => {
    dlg = useConfirmDialog()
    dlg.onCancel()
  })

  it('открывает диалог и резолвит true по подтверждению', async () => {
    const promise = dlg.confirm('Удалить дело?', 'Безвозвратно')
    expect(dlg.dialog.value.show).toBe(true)
    expect(dlg.dialog.value.title).toBe('Удалить дело?')
    expect(dlg.dialog.value.message).toBe('Безвозвратно')
    expect(dlg.dialog.value.confirmText).toBe('Удалить')

    dlg.onConfirm()
    await expect(promise).resolves.toBe(true)
    expect(dlg.dialog.value.show).toBe(false)
  })

  it('резолвит false по отмене', async () => {
    const promise = dlg.confirm('Точно?')
    dlg.onCancel()
    await expect(promise).resolves.toBe(false)
  })

  it('поддерживает свою подпись и цвет кнопки', () => {
    dlg.confirm('Снять юриста?', '', { confirmText: 'Снять', confirmColor: 'warning' })
    expect(dlg.dialog.value.confirmText).toBe('Снять')
    expect(dlg.dialog.value.confirmColor).toBe('warning')
    dlg.onCancel()
  })

  it('состояние общее для всех вызовов composable', () => {
    const other = useConfirmDialog()
    dlg.confirm('Общий стейт?')
    expect(other.dialog.value.show).toBe(true)
    other.onCancel()
    expect(dlg.dialog.value.show).toBe(false)
  })
})
