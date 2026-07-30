const EXTENSION_LANGUAGES = {
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',
  ts: 'typescript',
  tsx: 'typescript',
  py: 'python',
  pyw: 'python',
  json: 'json',
  sh: 'bash',
  bash: 'bash',
  zsh: 'bash',
  yml: 'yaml',
  yaml: 'yaml',
}

export function guessLanguage(filePath) {
  if (!filePath) return null

  const extension = filePath.split('.').pop()?.toLowerCase()
  return EXTENSION_LANGUAGES[extension] || null
}
