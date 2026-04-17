import { format, parseISO, isValid } from 'date-fns'
import { ru } from 'date-fns/locale'

export function formatDate(dateStr) {
  if (!dateStr) return '—'
  try {
    const d = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr
    return isValid(d) ? format(d, 'dd.MM.yyyy', { locale: ru }) : '—'
  } catch {
    return '—'
  }
}

export function formatDateTime(dateStr) {
  if (!dateStr) return '—'
  try {
    const d = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr
    return isValid(d) ? format(d, 'dd.MM.yyyy HH:mm', { locale: ru }) : '—'
  } catch {
    return '—'
  }
}

export function formatCurrency(amount, currency = '₽') {
  if (amount == null) return '—'
  return `${Number(amount).toLocaleString('ru-RU', { minimumFractionDigits: 2 })} ${currency}`
}

export function formatHours(hours) {
  if (hours == null) return '—'
  const h = parseFloat(hours)
  const whole = Math.floor(h)
  const mins = Math.round((h - whole) * 60)
  if (mins === 0) return `${whole}ч`
  return `${whole}ч ${mins}м`
}

export function formatFileSize(bytes) {
  if (!bytes) return '—'
  const units = ['Б', 'КБ', 'МБ', 'ГБ']
  let size = bytes
  for (const unit of units) {
    if (size < 1024) return `${size.toFixed(1)} ${unit}`
    size /= 1024
  }
  return `${size.toFixed(1)} ТБ`
}
