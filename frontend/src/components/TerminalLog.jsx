import { useEffect, useRef } from 'react'

function eventMessage(event) {
    const { step, status, data } = event
    if (step === 'RAG' && status === 'success')
        return `Retrieved ${data?.length || data?.context_length || 0} chars of context`
    if (step === 'Planner' && data?.plan)
        return `Plan: ${data.plan.length} sub-task(s) — ${data.plan.map(p => p.title).join(', ')}`
    if (step === 'CodeGenerator' && status === 'success')
        return `Generated ${data?.code_length || '?'} chars of code`
    if (step === 'Sandbox' && data?.phase === 'initial_run')
        return status === 'running' ? 'Running code in Docker sandbox…' : `Exit code ${data?.exit_code ?? '?'}`
    if (step === 'Sandbox' && data?.phase === 'test_run')
        return status === 'running'
            ? `Running tests (attempt ${data?.attempt})…`
            : `Tests ${data?.success ? 'passed ✓' : 'failed ✗'} (attempt ${data?.attempt})`
    if (step === 'TestGenerator')
        return status === 'running' ? 'Generating pytest suite…' : 'Test suite ready'
    if (step === 'Debugger')
        return `Analyzing error and patching (attempt ${data?.attempt})…`
    if (step === 'DebugLoop' && status === 'success')
        return `All tests passed after ${data?.attempts} attempt(s)`
    if (step === 'DebugLoop' && status === 'failed')
        return `Max debug attempts reached (${data?.attempts})`
    if (step === 'Refactor')
        return status === 'running' ? 'Refactoring for readability…' : 'Refactor complete'
    if (step === 'Pipeline' && status === 'success')
        return '— pipeline complete —'
    return data?.message || status
}

export default function TerminalLog({ events, running }) {
    const bottomRef = useRef(null)

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [events.length])

    if (events.length === 0 && !running) {
        return (
            <div className="empty-state">
                <div className="empty-icon">⬡</div>
                <div>Awaiting task</div>
                <div className="empty-hint">Enter a coding task and press Run</div>
            </div>
        )
    }

    return (
        <div className="terminal">
            {events.map((e) => (
                <div className="term-line" key={e.id}>
                    <span className="term-time">{e.timestamp}</span>
                    <span className={`term-step ${e.status}`}>{e.step}</span>
                    <span className="term-msg">{eventMessage(e)}</span>
                </div>
            ))}
            {running && (
                <div className="term-line">
                    <span className="term-time">—</span>
                    <span className="term-step running">working</span>
                    <span className="term-msg"><span className="term-cursor" /></span>
                </div>
            )}
            <div ref={bottomRef} />
        </div>
    )
}