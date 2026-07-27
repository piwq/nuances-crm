import { describe, it, expect } from 'vitest'
import { formatDate, formatDateTime, formatCurrency, formatHours, formatFileSize } from './formatters'

describe('formatDate', () => {
  it('печатает дату в российском порядке', () => {
    expect(formatDate('2026-08-01')).toBe('01.08.2026')
  })

  it('не падает на пустых и мусорных значениях', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDate('')).toBe('—')
    expect(formatDate('не дата')).toBe('—')
  })
})

describe('formatDateTime', () => {
  it('добавляет время', () => {
    expect(formatDateTime('2026-08-01T09:05:00')).toBe('01.08.2026 09:05')
  })
})

describe('formatCurrency', () => {
  it('форматирует суммы с копейками', () => {
    // неразрывные пробелы в русской локали — сравниваем по цифрам
    expect(formatCurrency(1234.5).replace(/\s/g, ' ')).toBe('1 234,50 ₽')
    expect(formatCurrency('0')).toContain('0,00')
  })

  it('пустое значение — прочерк', () => {
    expect(formatCurrency(null)).toBe('—')
  })
})

describe('formatHours', () => {
  it('целые часы без минут', () => {
    expect(formatHours(2)).toBe('2ч')
  })

  it('дробные часы переводит в минуты', () => {
    expect(formatHours(1.5)).toBe('1ч 30м')
    expect(formatHours('0.25')).toBe('0ч 15м')
  })
})

describe('formatFileSize', () => {
  it('подбирает единицу', () => {
    expect(formatFileSize(512)).toBe('512.0 Б')
    expect(formatFileSize(2048)).toBe('2.0 КБ')
    expect(formatFileSize(5 * 1024 * 1024)).toBe('5.0 МБ')
  })
})
