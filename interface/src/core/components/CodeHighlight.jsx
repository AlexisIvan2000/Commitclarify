import { useMemo } from 'react'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import python from 'highlight.js/lib/languages/python'
import typescript from 'highlight.js/lib/languages/typescript'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import yaml from 'highlight.js/lib/languages/yaml'
import 'highlight.js/styles/github-dark-dimmed.css'
import { guessLanguage } from '../utils/language'

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('yaml', yaml)

const MAX_LENGTH = 4000

function highlight(code, filePath) {
  const language = guessLanguage(filePath)

  try {
    return language
      ? hljs.highlight(code, { language }).value
      : hljs.highlightAuto(code).value
  } catch {
    return null
  }
}

function CodeHighlight({ code, filePath }) {
  const truncated = typeof code === 'string' ? code.slice(0, MAX_LENGTH) : ''
  const markup = useMemo(
    () => (truncated ? highlight(truncated, filePath) : null),
    [truncated, filePath],
  )

  if (!truncated) return null

  return (
    <pre className="issue-code-hint">
      {markup
        ? <code dangerouslySetInnerHTML={{ __html: markup }} />
        : <code>{truncated}</code>}
    </pre>
  )
}

export default CodeHighlight
