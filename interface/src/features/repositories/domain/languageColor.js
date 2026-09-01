const COLORS = {
  javascript: '#f1e05a',
  typescript: '#3178c6',
  python: '#3572a5',
  java: '#b07219',
  go: '#00add8',
  rust: '#dea584',
  php: '#4f5d95',
  ruby: '#701516',
  'c#': '#178600',
  'c++': '#f34b7d',
  c: '#555555',
  html: '#e34c26',
  css: '#563d7c',
  scss: '#c6538c',
  shell: '#89e051',
  dart: '#00b4ab',
  kotlin: '#a97bff',
  swift: '#f05138',
  vue: '#41b883',
  svelte: '#ff3e00',
}

export function languageColor(language) {
  if (!language) return 'var(--ink-ghost)'
  return COLORS[language.toLowerCase()] || 'var(--ink-ghost)'
}
