import React, { useState } from 'react'
import { Badge, Cite, Empty, statusTone } from './ui.jsx'

export default function CaseStudies({ result, evMap, onCite }) {
  const [key, setKey] = useState('gatekeeper')
  if (!result) return <Empty>Run the agents to generate case studies.</Empty>
  const v = result.versions.find((x) => x.key === key) || result.versions[0]
  return (
    <>
      <div className="mb-4 flex gap-2">
        {result.versions.map((x) => (
          <button key={x.key} onClick={() => setKey(x.key)}
                  className={`btn ${v.key === x.key ? 'bg-brand-700 text-white' : 'bg-white border border-slate-300'} capitalize`}>
            {x.key === 'user' ? 'Users' : x.key + 's'}
          </button>
        ))}
      </div>
      <article className="card p-8 max-w-3xl">
        <div className="mb-1 flex gap-2">
          <Badge tone={statusTone(v.status)}>{v.status.replace(/_/g, ' ')}</Badge>
          <Badge tone={v.grounding.ok ? 'green' : 'red'}>grounding {v.grounding.ok ? 'passed' : 'FAILED'} · {v.grounding.claims_checked} claims checked</Badge>
          <Badge tone={v.privacy_recheck?.passed ? 'green' : 'red'}>privacy {v.privacy_recheck?.passed ? 'clear' : 'leak'}</Badge>
        </div>
        <h1 className="mt-3 text-2xl font-bold text-brand-900">{v.title}</h1>
        <p className="text-sm text-slate-500">For {v.audience}</p>
        {v.grounding.issues.map((i, n) => <p key={n} className="mt-2 text-sm text-rose-700">{i.section}: {i.issue}</p>)}
        {v.sections.map((s) => (
          <section key={s.heading} className="mt-6">
            <h2 className="border-b border-slate-200 pb-1 text-lg font-semibold">{s.heading}</h2>
            <ul className="mt-3 space-y-3">
              {s.claims.map((c, i) => (
                <li key={i} className={c.type === 'quote' ? 'border-l-4 border-brand-500 bg-brand-50 p-3 italic' : 'text-slate-700'}>
                  {c.text}{c.refs.map((r) => <Cite key={r} refId={r} evidence={evMap} onOpen={onCite} />)}
                  {c.type === 'quote' && <Badge tone="amber">needs client consent</Badge>}
                  {c.calc && <div className="mt-1 font-mono text-xs not-italic text-slate-500">Calculation: {c.calc}</div>}
                </li>
              ))}
            </ul>
          </section>
        ))}
        {v.sections.length === 0 && <p className="mt-6 text-slate-500">No verified content was available for this audience.</p>}
      </article>
    </>
  )
}
