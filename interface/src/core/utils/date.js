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
