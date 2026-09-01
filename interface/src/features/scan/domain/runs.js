export const SCAN = 'scan'
export const DEEPEN = 'deepen'

export const SLOW_AFTER_SECONDS = {
  [SCAN]: 60,
  [DEEPEN]: 120,
}

export function slowThreshold(phase) {
  return SLOW_AFTER_SECONDS[phase] ?? SLOW_AFTER_SECONDS[SCAN]
}
