import { useState } from 'react'

function highlight(code) {
    // Minimal but readable syntax highlighting via regex replacements
    return code
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        // Comments
        .replace(/(#[^\n]*)/g, '<span class="cm">$1</span>')
        // Decorators
        .replace(/(@\w+)/g, '<span class="dec">$1</span>')
        // Keywords
        .replace(/\b(def|class|return|import|from|if|else|elif|for|while|try|except|finally|with|as|pass|raise|yield|async|await|lambda|not|and|or|in|is|True|False|None)\b/g,
            '<span class="kw">$1</span>')
        // Strings
        .replace(/("""[\s\S]*?"""|'''[\s\S]*?'''|"[^"]*"|'[^']*')/g,
            '<span class="str">$1</span>')
        // Function names
        .replace(/\b([a-z_]\w*)\s*(?=\()/g, '<span class="fn">$1</span>')
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