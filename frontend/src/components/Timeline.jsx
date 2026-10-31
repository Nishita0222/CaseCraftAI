import React from 'react'
import { Badge, Cite, Empty, Section } from './ui.jsx'

export default function Timeline({ result, evMap, onCite }) {
  if (!result) return <Empty>Run the agents to build the timeline.</Empty>
  const { timeline = [], scope_changes = [], undated = [], span } = result
  return (
    <>
      <Section title="Project timeline" right={span && <Badge tone="teal">span {span.days} days</Badge>}>
        {timeline.length === 0 ? <Empty>No dated milestones found in the evidence.</Empty> : (
          <ol className="relative ml-3 border-l-2 border-brand-100 pl-6 space-y-4">
            {timeline.map((t, i) => (
              <li key={i} className="relative">
                <span className={`absolute -left-[33px] top-1 h-3.5 w-3.5 rounded-full border-2 border-white ${t.type === 'scope' ? 'bg-amber-500' : 'bg-brand-600'}`} />
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-semibold">{t.date}</span>
                  <Badge tone={t.type === 'scope' ? 'amber' : 'teal'}>{t.type}</Badge>
                  <Cite refId={t.ref} evidence={evMap} onOpen={onCite} />
                </div>
                <p className="text-sm text-slate-600 mt-0.5">{t.text}</p>
                {t.note && <p className="text-xs text-amber-700">{t.note}</p>}
              </li>
            ))}
          </ol>
        )}
        {span && <p className="mt-3 text-xs text-slate-500">Calculation: {span.calc} (first → last milestone) <Cite refId={span.refs[0]} evidence={evMap} onOpen={onCite} /><Cite refId={span.refs[1]} evidence={evMap} onOpen={onCite} /></p>}
      </Section>
      <Section title={`Scope changes (${scope_changes.length})`}>
        {scope_changes.length === 0 ? <Empty>No scope changes detected.</Empty> : (
          <div className="grid gap-2">
            {scope_changes.map((s, i) => (
              <div key={i} className="card p-3 text-sm">
                <div className="flex items-center gap-2 mb-1">
                  <Badge tone="amber">{s.type}</Badge>
                  {s.date && <span className="text-slate-500">dated {s.date}</span>}
                  {s.communicated && <span className="text-slate-400">· communicated {s.communicated}</span>}
                  <Cite refId={s.ref} evidence={evMap} onOpen={onCite} />
                </div>
                {s.text}
              </div>
            ))}
          </div>
        )}
      </Section>
      {undated.length > 0 && (
        <Section title="Undated items (not placed on the timeline)">
          <ul className="card divide-y divide-slate-100 text-sm">
            {undated.map((u, i) => <li key={i} className="p-3"><Badge>{u.type}</Badge> {u.text} <Cite refId={u.ref} evidence={evMap} onOpen={onCite} /></li>)}
          </ul>
        </Section>
      )}
    </>
  )
}
