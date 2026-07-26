// Расчёт процессуального срока: N дней или месяцев от даты события.
// Если окончание выпадает на выходной — переносится на ближайший рабочий день
// (ст. 108 ГПК РФ). Праздничные дни не учитываются — сверяйтесь с
// производственным календарём.
export function calcDeadline(startDate, amount, unit) {
  if (!startDate || !amount || amount < 1) return null
  const d = new Date(`${startDate}T00:00:00`)
  if (Number.isNaN(d.getTime())) return null

  if (unit === 'months') {
    const day = d.getDate()
    d.setDate(1)
    d.setMonth(d.getMonth() + Number(amount))
    const lastDay = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate()
    d.setDate(Math.min(day, lastDay))
  } else {
    d.setDate(d.getDate() + Number(amount))
  }

  let shifted = false
  while (d.getDay() === 0 || d.getDay() === 6) {
    d.setDate(d.getDate() + 1)
    shifted = true
  }

  const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  return { date: iso, shifted }
}
