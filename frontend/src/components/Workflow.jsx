import React from 'react'
import { Badge, statusTone, Section } from './ui.jsx'

const ICON = { pending: '○', running: '◔', done: '●', failed: '✕' }

export default function Workflow({ run, onRun, busy, hasDocs }) {
  const steps = run?.steps || []
  const done = steps.filter((s) => s.status === 'done').length
  return (
    <Section
      title="Agent workflow (LangGraph)"
      right={<button className="btn-primary" disabled={busy || !hasDocs || run?.status === 'running'} onClick={onRun}>
        {run?.status === 'running' ? 'Running…' : 'Run all agents'}</button>}
    >
      {!hasDocs && <p className="text-sm text-amber-700 mb-3">Upload at least one document to start.</p>}
      {run && (
        <div className="mb-3 flex items-center gap-3 text-sm">
          <Badge tone={statusTone(run.status)}>{run.status}</Badge>
          {run.engine && <Badge tone="slate">engine: {run.engine}</Badge>}
          <div className="h-2 flex-1 rounded bg-slate-200 overflow-hidden">
            <div className="h-full bg-brand-600 transition-all" style={{ width: `${(done / Math.max(steps.length, 1)) * 100}%` }} />
          </div>
          <span className="text-slate-500">{done}/{steps.length}</span>
        </div>
      )}
      {run?.error && <p className="mb-3 rounded bg-rose-50 p-3 text-sm text-rose-700">Run failed: {run.error}</p>}
      <ol className="grid gap-2 md:grid-cols-2">
        {steps.map((s, i) => (
          <li key={s.id} className="card p-3 flex gap-3">
            <span className={`text-xl leading-none ${s.status === 'done' ? 'text-emerald-600' : s.status === 'running' ? 'text-sky-600 animate-pulse' : s.status === 'failed' ? 'text-rose-600' : 'text-slate-300'}`}>
              {ICON[s.status] || '○'}
            </span>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{i + 1}. {s.label}</span>
                <Badge tone={statusTone(s.status)}>{s.status}</Badge>
              </div>
              <p className="text-xs text-slate-500 mt-0.5 break-words">{s.message || '—'}</p>
            </div>
          </li>
        ))}
      </ol>
      {!run && <p className="text-sm text-slate-500">No run yet. Eight agents will run in order: read → timeline → KPIs → privacy → write → re-check → media → approval pack.</p>}
    </Section>
  )
}
