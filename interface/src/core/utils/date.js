const HAS_TIMEZONE = /(Z|[+-]\d{2}:?\d{2})$/

function toDate(value) {
  if (!value) return null

  const normalized = HAS_TIMEZONE.test(value) ? value : `${value}Z`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDateTime(value) {
  const date = toDate(value)
  if (!date) return ''

  return date.toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatShortDateTime(value) {
  const date = toDate(value)
  if (!date) return ''

  return date.toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatMonthYear(value) {
  const date = toDate(value)
  if (!date) return ''

  return date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })
}

const MINUTE = 60
const HOUR = MINUTE * 60
const DAY = HOUR * 24
const MONTH = DAY * 30

export function formatRelative(value, strings) {
  const date = toDate(value)
  if (!date) return ''

  const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000))

  if (seconds < MINUTE) return strings.justNow
  if (seconds < HOUR) return strings.minutes.replace('{count}', Math.floor(seconds / MINUTE))
  if (seconds < DAY) return strings.hours.replace('{count}', Math.floor(seconds / HOUR))
  if (seconds < MONTH) return strings.days.replace('{count}', Math.floor(seconds / DAY))

  return strings.months.replace('{count}', Math.floor(seconds / MONTH))
}
