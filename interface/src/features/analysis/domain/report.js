export function resultsByAspect(analysis) {
  const map = {}

  for (const result of analysis?.results || []) {
    if (result?.aspect) map[result.aspect] = result
  }

  return map
}

export function hasResults(analysis) {
  return Object.keys(resultsByAspect(analysis)).length > 0
}
