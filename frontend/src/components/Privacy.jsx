import React from 'react'
import { Badge, Cite, Empty, Section, Table } from './ui.jsx'

const ACTION_TONE = { redact: 'amber', anonymize: 'blue', restrict: 'red' }

export default function Privacy({ result, evMap, onCite }) {
  if (!result) return <Empty>Run the agents to scan for confidential information.</Empty>
  const p = result.privacy
  return (
    <>
      <Section title="Privacy & NDA status" right={<Badge tone={p.recheck?.passed ? 'green' : 'red'}>{p.recheck?.passed ? 'Re-check passed: no leaks' : 'Leaks found — outputs blocked'}</Badge>}>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="card p-4">
            <h3 className="mb-2 text-sm font-semibold">Rules applied</h3>
            <ul className="list-disc pl-5 text-sm text-slate-600 space-y-1">{p.rules.map((r) => <li key={r}>{r}</li>)}</ul>
          </div>
          <div className="card p-4">
            <h3 className="mb-2 text-sm font-semibold">Findings by type</h3>
            <div className="flex flex-wrap gap-2">{Object.entries(p.counts).map(([k, v]) => <Badge key={k} tone="slate">{k}: {v}</Badge>)}{Object.keys(p.counts).length === 0 && <span className="text-sm text-slate-500">none</span>}</div>
            <h3 className="mt-4 mb-1 text-sm font-semibold">Restricted sentences (never used)</h3>
            <div className="text-sm">{p.restricted_refs.map((r) => <Cite key={r} refId={r} evidence={evMap} onOpen={onCite} />)}{p.restricted_refs.length === 0 && 'none'}</div>
          </div>
        </div>
      </Section>
      <Section title={`Findings (${p.findings.length})`}>
        <Table head={['Type', 'Match', 'Action', 'Severity', 'Source']}>
          {p.findings.map((f) => (
            <tr key={f.id}>
              <td className="td">{f.type}</td>
              <td className="td font-mono text-xs break-all">{f.match}</td>
              <td className="td"><Badge tone={ACTION_TONE[f.action]}>{f.action}</Badge>{f.note && <div className="text-xs text-slate-500 mt-1">{f.note}</div>}</td>
              <td className="td">{f.severity}</td>
              <td className="td"><Cite refId={f.ref} evidence={evMap} onOpen={onCite} /></td>
            </tr>
          ))}
        </Table>
      </Section>
    </>
  )
}
