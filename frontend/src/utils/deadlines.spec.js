import { describe, it, expect } from 'vitest'
import { calcDeadline } from './deadlines'

describe('calcDeadline', () => {
  it('добавляет дни', () => {
    // 02.03.2026 (пн) + 3 = четверг, переносить нечего
    expect(calcDeadline('2026-03-02', 3, 'days')).toEqual({ date: '2026-03-05', shifted: false })
  })

  it('переносит выходные на ближайший рабочий день', () => {
    // +5 = суббота 07.03 → понедельник 09.03
    expect(calcDeadline('2026-03-02', 5, 'days')).toEqual({ date: '2026-03-09', shifted: true })
  })

  it('считает месяцы, а не 30 дней', () => {
    expect(calcDeadline('2026-01-15', 1, 'months').date).toBe('2026-02-16')  // 15.02 — вс
    expect(calcDeadline('2026-04-15', 1, 'months')).toEqual({ date: '2026-05-15', shifted: false })
  })

  it('прижимает к последнему дню короткого месяца', () => {
    expect(calcDeadline('2026-01-31', 1, 'months').date).toBe('2026-03-02')  // 28.02 — сб
    expect(calcDeadline('2026-03-31', 1, 'months')).toEqual({ date: '2026-04-30', shifted: false })
  })

  it('переваливает через год', () => {
    expect(calcDeadline('2026-12-10', 1, 'months')).toEqual({ date: '2027-01-11', shifted: true })
  })

  it('возвращает null на пустых или некорректных данных', () => {
    expect(calcDeadline('', 5, 'days')).toBeNull()
    expect(calcDeadline('2026-03-02', 0, 'days')).toBeNull()
    expect(calcDeadline('не дата', 5, 'days')).toBeNull()
  })
})
