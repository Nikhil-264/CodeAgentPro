import { useState } from 'react'

function highlight(code) {
    if (!code) return ''
    
    const tokens = []
    function storeToken(match, cls) {
        tokens.push(`<span class="${cls}">${match}</span>`)
        return `___TOKEN_${tokens.length - 1}___`
    }

    // 1. Escape HTML entity chars
    let escaped = code
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')

    // 2. Extract strings & comments into safe tokens FIRST
    escaped = escaped
        .replace(/("""[\s\S]*?"""|'''[\s\S]*?'''|"[^"]*"|'[^']*')/g, m => storeToken(m, 'str'))
        .replace(/(\/\/[^\n]*|\/\*[\s\S]*?\*\/|#[^\n]*)/g, m => storeToken(m, 'cm'))

    // 3. Highlight keywords across Python, JavaScript, and C++
    escaped = escaped.replace(
        /\b(def|class|struct|enum|union|return|import|from|include|using|namespace|if|else|elif|for|while|do|switch|case|default|try|catch|except|finally|with|as|pass|raise|yield|async|await|lambda|not|and|or|in|is|True|False|None|true|false|nullptr|null|const|constexpr|auto|int|float|double|char|bool|void|size_t|std|vector|string|map|set|list|new|delete|public|private|protected)\b/g,
        '<span class="kw">$1</span>'
    )

    // 4. Highlight function names
    escaped = escaped.replace(/\b([a-zA-Z_]\w*)\s*(?=\()/g, '<span class="fn">$1</span>')

    // 5. Restore stored tokens
    escaped = escaped.replace(/___TOKEN_(\d+)___/g, (_, id) => tokens[parseInt(id, 10)])

    return escaped
}

export default function CodeViewer({ code, filename = 'solution.py', label }) {
    const [copied, setCopied] = useState(false)

    const copy = async () => {
        await navigator.clipboard.writeText(code)
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
    }

    if (!code) return null

    return (
        <div>
            {label && <div className="section-title">{label}</div>}
            <div className="code-block">
                <div className="code-header">
                    <span className="code-filename">{filename}</span>
                    <button className="copy-btn" onClick={copy}>
                        {copied ? '✓ copied' : 'copy'}
                    </button>
                </div>
                <div className="code-body">
                    <pre dangerouslySetInnerHTML={{ __html: highlight(code) }} />
                </div>
            </div>
        </div>
    )
}