import { useState, useCallback, useRef } from 'react'

const API = 'http://localhost:8000/api'

const INITIAL_STATE = {
  status: 'idle',       // idle | running | success | failed
  events: [],
  currentCode: '',
  testCode: '',
  execOutput: { stdout: '', stderr: '', success: false },
  ragStats: null,
  error: null,
}

export function useAgent() {
  const [state, setState] = useState(INITIAL_STATE)
  const abortRef = useRef(null)

  const updateState = (patch) => setState(s => ({ ...s, ...patch }))

  // ── Run pipeline ─────────────────────────────────────────────────────────
  const run = useCallback(async (config) => {
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setState({ ...INITIAL_STATE, status: 'running' })

    try {
      const res = await fetch(`${API}/generate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
        signal: controller.signal,
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (raw === '[DONE]') {
            updateState({ status: 'success' })
            continue
          }
          try {
            const event = JSON.parse(raw)
            processEvent(event)
          } catch { }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') return
      updateState({ status: 'failed', error: err.message })
    }
  }, [])

  // ── Process incoming SSE events ──────────────────────────────────────────
  const processEvent = useCallback((event) => {
    const { step, status, data } = event

    setState(s => {
      const timestamp = new Date().toLocaleTimeString('en', { hour12: false })
      const newEvent = { step, status, data, timestamp, id: Date.now() + Math.random() }
      const events = [...s.events, newEvent]

      let patch = { events }

      // Extract code from pipeline events
      if (step === 'CodeGenerator' && status === 'success' && data?.code) {
        patch.currentCode = data.code
      }
      if (step === 'TestGenerator' && status === 'success' && data?.test_code) {
        patch.testCode = data.test_code
      }
      if (step === 'Refactor' && status === 'success' && (data?.refactored_code || data?.code)) {
        patch.currentCode = data.refactored_code || data.code
      }
      if (step === 'Pipeline' && status === 'success' && data?.final_code) {
        patch.currentCode = data.final_code
        patch.testCode = data.test_code || ''
        patch.status = 'success'
      }

      // Capture sandbox output
      if (step === 'Sandbox' && data?.stdout !== undefined) {
        patch.execOutput = {
          stdout: data.stdout,
          stderr: data.stderr,
          success: data.success,
        }
      }

      // Fatal error
      if (step === 'CodeGenerator' && status === 'failed') {
        patch.status = 'failed'
        patch.error = data?.error || 'Code generation failed'
      }

      return { ...s, ...patch }
    })
  }, [])

  // ── RAG operations ───────────────────────────────────────────────────────
  const fetchRagStats = useCallback(async () => {
    try {
      const res = await fetch(`${API}/rag/stats`)
      const data = await res.json()
      updateState({ ragStats: data })
    } catch { }
  }, [])

  const seedDocs = useCallback(async () => {
    try {
      await fetch(`${API}/rag/seed-docs`, { method: 'POST' })
      await fetchRagStats()
    } catch { }
  }, [fetchRagStats])

  const stop = useCallback(() => {
    abortRef.current?.abort()
    updateState({ status: 'idle' })
  }, [])

  return { state, run, stop, fetchRagStats, seedDocs }
}