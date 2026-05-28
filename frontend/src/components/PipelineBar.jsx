import React, { useMemo } from 'react'

const NODES = [
    { key: 'RAG', label: 'RAG', icon: '◈' },
    { key: 'Planner', label: 'Plan', icon: '⊞' },
    { key: 'CodeGenerator', label: 'Generate', icon: '⌨' },
    { key: 'Sandbox', label: 'Execute', icon: '▶' },
    { key: 'TestGenerator', label: 'Tests', icon: '⚡' },
    { key: 'DebugLoop', label: 'Debug', icon: '⚙' },
    { key: 'Refactor', label: 'Refactor', icon: '✦' },
    { key: 'Pipeline', label: 'Done', icon: '✓' },
]

export default function PipelineBar({ events }) {
    const nodeStatus = useMemo(() => {
        const map = {}
        for (const e of events) {
            let key = e.step
            if (key === 'Debugger') key = 'DebugLoop'
            // Once success/failed is set, don't overwrite with a later 'running'
            const prev = map[key]
            if (prev === 'success' || prev === 'failed') continue
            map[key] = e.status
        }
        return map
    }, [events])

    return (
        <div className="pipeline-bar">
            {NODES.map((node, i) => {
                const status = nodeStatus[node.key] || 'idle'
                return (
                    <React.Fragment key={node.key}>
                        <div className={`pipeline-node ${status}`}>
                            <div className="node-icon">{node.icon}</div>
                            <span className="node-name">{node.label}</span>
                        </div>
                        {i < NODES.length - 1 && (
                            <span className="node-arrow">›</span>
                        )}
                    </React.Fragment>
                )
            })}
        </div>
    )
}