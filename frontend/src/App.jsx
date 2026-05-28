import { useState, useEffect } from 'react'
import { useAgent } from './useAgent'
import PipelineBar from './components/PipelineBar'
import TerminalLog from './components/TerminalLog'
import CodeViewer from './components/CodeViewer'

const EXAMPLE_TASKS = [
  'Write a Python function that finds all prime numbers up to N using the Sieve of Eratosthenes',
  'Build a simple REST API with FastAPI for a todo list with CRUD operations',
  'Write a binary search implementation with comprehensive edge case handling',
  'Create a Python class for a stack data structure with push, pop, peek, and is_empty methods',
]

export default function App() {
  const { state, run, stop, fetchRagStats, seedDocs } = useAgent()
  const [activeTab, setActiveTab] = useState('terminal')
  const [ollamaOk, setOllamaOk] = useState(null)

  // Config form state
  const [task, setTask] = useState('')
  const [language, setLanguage] = useState('Python')
  const [framework, setFramework] = useState('standard library')
  const [model, setModel] = useState('deepseek-coder:6.7b')
  const [skipTests, setSkipTests] = useState(false)
  const [skipRefactor, setSkipRefactor] = useState(false)

  const running = state.status === 'running'

  // On mount: check Ollama + fetch RAG stats
  useEffect(() => {
    fetch('http://localhost:8000/api/health/ollama')
      .then(r => r.json())
      .then(d => setOllamaOk(d.ollama_running))
      .catch(() => setOllamaOk(false))
    fetchRagStats()
  }, [])

  // Auto-switch to terminal tab when pipeline starts
  useEffect(() => {
    if (running) setActiveTab('terminal')
  }, [running])

  // Auto-switch to code tab when code arrives
  useEffect(() => {
    if (state.currentCode && !running) setActiveTab('code')
  }, [state.currentCode])

  const handleRun = () => {
    if (!task.trim()) return
    run({ task, language, framework, model, skip_tests: skipTests, skip_refactor: skipRefactor })
  }

  const handleStop = () => stop()

  const codeEventCount = state.events.filter(e => e.step === 'CodeGenerator' && e.status === 'success').length

  return (
    <div className="app">
      {/* ── Header ─────────────────────────────────────── */}
      <header className="header">
        <div className="header-logo">
          <div className="logo-mark">CA</div>
          <div>
            <div className="header-title">CodeAgent Pro</div>
            <div className="header-subtitle">AGENTIC AI CODING SYSTEM</div>
          </div>
        </div>
        <div className="header-spacer" />
        <div className="status-badge">
          <div className={`status-dot ${ollamaOk === true ? 'online' : ollamaOk === false ? 'error' : ''}`} />
          {ollamaOk === true ? 'Ollama online' : ollamaOk === false ? 'Ollama offline' : 'Checking…'}
        </div>
      </header>

      <div className="main-layout">
        {/* ── Left Panel ─────────────────────────────────── */}
        <aside className="input-panel">

          {/* Task input */}
          <div className="panel-section">
            <div className="section-label">Task</div>
            <textarea
              className="task-input"
              placeholder="Describe what you want the agent to build…"
              value={task}
              onChange={e => setTask(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) handleRun() }}
              disabled={running}
            />
            <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {EXAMPLE_TASKS.map((ex, i) => (
                <button
                  key={i}
                  onClick={() => setTask(ex)}
                  disabled={running}
                  style={{
                    padding: '3px 8px',
                    background: 'transparent',
                    border: '1px solid var(--border)',
                    borderRadius: 4,
                    color: 'var(--text-muted)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 10,
                    cursor: 'pointer',
                    transition: 'all 0.18s',
                  }}
                  onMouseEnter={e => e.target.style.borderColor = 'var(--green-dim)'}
                  onMouseLeave={e => e.target.style.borderColor = 'var(--border)'}
                >
                  eg. {i + 1}
                </button>
              ))}
            </div>
          </div>

          {/* Config */}
          <div className="panel-section">
            <div className="section-label">Configuration</div>
            <div className="config-row">
              <label className="config-label">Model</label>
              <input className="config-input" value={model} onChange={e => setModel(e.target.value)} disabled={running} />
            </div>
            <div className="config-row">
              <label className="config-label">Language</label>
              <select className="config-select" value={language} onChange={e => setLanguage(e.target.value)} disabled={running}>
                <option>Python</option>
                <option>JavaScript</option>
                <option>TypeScript</option>
                <option>Go</option>
              </select>
            </div>
            <div className="config-row">
              <label className="config-label">Framework</label>
              <input className="config-input" value={framework} onChange={e => setFramework(e.target.value)} disabled={running} />
            </div>
            <div className="toggle-row">
              <span className="toggle-label">Skip tests</span>
              <label className="toggle">
                <input type="checkbox" checked={skipTests} onChange={e => setSkipTests(e.target.checked)} disabled={running} />
                <span className="toggle-slider" />
              </label>
            </div>
            <div className="toggle-row">
              <span className="toggle-label">Skip refactor</span>
              <label className="toggle">
                <input type="checkbox" checked={skipRefactor} onChange={e => setSkipRefactor(e.target.checked)} disabled={running} />
                <span className="toggle-slider" />
              </label>
            </div>
          </div>

          {/* Run / Stop */}
          <div className="panel-section">
            {running ? (
              <button className="run-btn running" onClick={handleStop}>
                ■ Stop Agent
              </button>
            ) : (
              <button className="run-btn" onClick={handleRun} disabled={!task.trim() || ollamaOk === false}>
                ▶ Run Agent
                <span style={{ opacity: 0.6, fontSize: 10 }}>ctrl+enter</span>
              </button>
            )}
            {state.error && (
              <div style={{ marginTop: 8, padding: '6px 10px', background: '#200a0a', border: '1px solid var(--red)', borderRadius: 4, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--red)' }}>
                {state.error}
              </div>
            )}
          </div>

          {/* RAG Stats */}
          <div className="panel-section">
            <div className="section-label">RAG Knowledge Base</div>
            {state.ragStats?.available === false ? (
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
                chromadb not installed
              </div>
            ) : (
              <>
                <div className="rag-stats">
                  <div className="rag-stat">
                    <div className="rag-stat-value">{state.ragStats?.codebase_chunks ?? '—'}</div>
                    <div className="rag-stat-label">Codebase</div>
                  </div>
                  <div className="rag-stat">
                    <div className="rag-stat-value">{state.ragStats?.doc_chunks ?? '—'}</div>
                    <div className="rag-stat-label">Docs</div>
                  </div>
                  <div className="rag-stat">
                    <div className="rag-stat-value">{state.ragStats?.error_fixes ?? '—'}</div>
                    <div className="rag-stat-label">Fixes</div>
                  </div>
                </div>
                <button className="rag-btn" onClick={seedDocs}>↳ Seed built-in docs</button>
              </>
            )}
          </div>
        </aside>

        {/* ── Right Panel ─────────────────────────────────── */}
        <main className="output-panel">
          <PipelineBar events={state.events} />

          <div className="content-area">
            <div className="tab-bar">
              <button className={`tab ${activeTab === 'terminal' ? 'active' : ''}`} onClick={() => setActiveTab('terminal')}>
                Terminal
                {state.events.length > 0 && <span className="badge">{state.events.length}</span>}
              </button>
              <button className={`tab ${activeTab === 'code' ? 'active' : ''}`} onClick={() => setActiveTab('code')}>
                Code
              </button>
              <button className={`tab ${activeTab === 'tests' ? 'active' : ''}`} onClick={() => setActiveTab('tests')}>
                Tests
              </button>
              <button className={`tab ${activeTab === 'output' ? 'active' : ''}`} onClick={() => setActiveTab('output')}>
                Exec Output
              </button>
            </div>

            <div className="tab-content">
              {activeTab === 'terminal' && (
                <TerminalLog events={state.events} running={running} />
              )}

              {activeTab === 'code' && (
                state.currentCode
                  ? <CodeViewer code={state.currentCode} filename="solution.py" />
                  : <div className="empty-state"><div className="empty-icon">⌨</div><div>No code yet</div></div>
              )}

              {activeTab === 'tests' && (
                state.testCode
                  ? <CodeViewer code={state.testCode} filename="test_solution.py" />
                  : <div className="empty-state"><div className="empty-icon">⚡</div><div>No tests yet</div></div>
              )}

              {activeTab === 'output' && (
                state.execOutput.stdout || state.execOutput.stderr ? (
                  <div>
                    {state.execOutput.stdout && (
                      <>
                        <div className="section-title">stdout</div>
                        <div className={`exec-output ${state.execOutput.success ? 'success' : 'failed'}`}>
                          {state.execOutput.stdout}
                        </div>
                      </>
                    )}
                    {state.execOutput.stderr && (
                      <>
                        <div className="section-title">stderr</div>
                        <div className="exec-output failed">{state.execOutput.stderr}</div>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="empty-state"><div className="empty-icon">▶</div><div>No execution output yet</div></div>
                )
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}