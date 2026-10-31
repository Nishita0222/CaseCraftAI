import React from 'react'
import { Badge, Cite, Empty, Section, statusTone } from './ui.jsx'

export default function Kpis({ result, evMap, onCite }) {
  if (!result) return <Empty>Run the agents to verify KPIs.</Empty>
  const kpis = result.kpis || []
  return (
    <Section title="KPI verification report">
      <p className="mb-3 text-sm text-slate-500">Every figure is recalculated from the baseline and result found in the documents. Conflicting sources are resolved by authority (measured data &gt; reports &gt; emails; final &gt; preliminary). Unresolved or confidential KPIs never reach a case study.</p>
      {kpis.length === 0 && <Empty>No KPI claims (“reduced X from A to B”, or a KPI/Baseline/Result table) were found.</Empty>}
      <div className="grid gap-3">
        {kpis.map((k) => (
          <div key={k.id} className="card p-4">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold">{k.kpi}</h3>
              <Badge tone={statusTone(k.status)}>{k.status.replace('_', ' ')}</Badge>
              {k.usable ? <Badge tone="green">used in case studies</Badge> : <Badge tone="red">excluded</Badge>}
            </div>
            <div className="mt-3 grid grid-cols-3 gap-3 text-center">
              <div className="rounded-lg bg-slate-50 p-3"><div className="text-xs text-slate-500">Baseline</div><div className="text-xl font-semibold">{k.baseline}<span className="text-sm text-slate-400"> {k.unit}</span></div></div>
              <div className="rounded-lg bg-slate-50 p-3"><div className="text-xs text-slate-500">Result</div><div className="text-xl font-semibold">{k.result}<span className="text-sm text-slate-400"> {k.unit}</span></div></div>
              <div className="rounded-lg bg-brand-50 p-3"><div className="text-xs text-slate-500">Change</div><div className="text-xl font-semibold text-brand-700">{k.pct_change ? `${k.pct_change}%` : 'n/a'}</div></div>
            </div>
            <p className="mt-3 font-mono text-xs bg-slate-900 text-emerald-300 rounded px-3 py-2 overflow-x-auto">{k.calc}</p>
            <div className="mt-2 text-sm">Sources: {k.refs.map((r) => <Cite key={r} refId={r} evidence={evMap} onOpen={onCite} />)}</div>
            {k.rationale && <p className="mt-2 text-sm text-slate-600"><b>Resolution:</b> {k.rationale}</p>}
            {k.overridden.length > 0 && (
              <p className="mt-1 text-xs text-slate-500">Overridden: {k.overridden.map((o) => <span key={o.ref}><Cite refId={o.ref} evidence={evMap} onOpen={onCite} />{o.baseline}→{o.result} </span>)}</p>
            )}
            {k.warnings.map((w, i) => <p key={i} className="mt-1 text-xs text-amber-700">⚠ {w}</p>)}
          </div>
        ))}
      </div>
    </Section>
  )
}
