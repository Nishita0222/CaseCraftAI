import React, { useEffect, useMemo, useState } from 'react'
import { Badge, Empty, Section } from './ui.jsx'

export default function Evidence({ result, focus }) {
  const [q, setQ] = useState('')
  const [doc, setDoc] = useState('all')
  useEffect(() => { if (focus) { setQ(focus); setDoc('all') } }, [focus])
  const ev = result?.evidence || []
  const docs = useMemo(() => [...new Set(ev.map((e) => e.doc))], [ev])
  const restricted = new Set(result?.privacy?.restricted_refs || [])
  const shown = ev.filter((e) => (doc === 'all' || e.doc === doc) &&
    (!q || e.ref.toLowerCase() === q.toLowerCase() || e.text.toLowerCase().includes(q.toLowerCase())))
  if (!result) return <Empty>Run the agents to see extracted evidence.</Empty>
  return (
    <Section title={`Evidence register (${shown.length}/${ev.length})`}>
      <div className="mb-3 flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search text or reference (e.g. E012)…"
               className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <select value={doc} onChange={(e) => setDoc(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
          <option value="all">All documents</option>{docs.map((d) => <option key={d}>{d}</option>)}
        </select>
      </div>
      {result.warnings?.length > 0 && <ul className="mb-3 rounded bg-amber-50 p-3 text-sm text-amber-800 list-disc pl-6">{result.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>}
      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead><tr><th className="th">Ref</th><th className="th">Source</th><th className="th">Evidence text (original)</th><th className="th">Tags</th></tr></thead>
          <tbody>
            {shown.map((e) => (
              <tr key={e.ref} className={focus === e.ref ? 'bg-amber-50' : ''}>
                <td className="td font-mono text-brand-700">{e.ref}</td>
                <td className="td text-xs text-slate-500">{e.doc}<br />{e.location}</td>
                <td className="td">{e.text}</td>
                <td className="td space-x-1">
                  {restricted.has(e.ref) && <Badge tone="red">restricted</Badge>}
                  {e.tags.filter((t) => t !== 'restricted').map((t) => <Badge key={t}>{t}</Badge>)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-slate-500">Raw evidence is shown here for your review only. It is never included in exports.</p>
    </Section>
  )
}
