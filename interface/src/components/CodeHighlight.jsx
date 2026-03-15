import { useEffect, useRef } from 'react'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import python from 'highlight.js/lib/languages/python'
import typescript from 'highlight.js/lib/languages/typescript'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import yaml from 'highlight.js/lib/languages/yaml'
import 'highlight.js/styles/github-dark-dimmed.css'

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('yaml', yaml)

function guessLanguage(filePath) {
  if (!filePath) return null
  const ext = filePath.split('.').pop()?.toLowerCase()
  const map = {
    js: 'javascript', jsx: 'javascript', mjs: 'javascript',
    ts: 'typescript', tsx: 'typescript',
    py: 'python', pyw: 'python',
    json: 'json',
    sh: 'bash', bash: 'bash',
    yml: 'yaml', yaml: 'yaml',
  }
  return map[ext] || null
}

function CodeHighlight({ code, filePath }) {
  const codeRef = useRef(null)

  useEffect(() => {
    if (codeRef.current && code) {
      const lang = guessLanguage(filePath)
      if (lang) {
        try {
          const result = hljs.highlight(code, { language: lang })
          codeRef.current.innerHTML = result.value
        } catch {
          codeRef.current.textContent = code
        }
      } else {
        try {
          const result = hljs.highlightAuto(code)
          codeRef.current.innerHTML = result.value
        } catch {
          codeRef.current.textContent = code
        }
      }
    }
  }, [code, filePath])

  if (!code) return null

  return (
    <pre className="issue-code-hint">
      <code ref={codeRef}>{code}</code>
    </pre>
  )
}

export default CodeHighlight
