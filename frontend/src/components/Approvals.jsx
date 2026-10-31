import React, { useState } from 'react'
import { api } from '../api.js'
import { Badge, Empty, Section, Table, statusTone } from './ui.jsx'

export default function Approvals({ project, run, approvals, audit, onChange, onError }) {
  const [reviewer, setReviewer] = useState('')
  const [comment, setComment] = useState('')
  const [exp, setExp] = useState(null)
  if (!run?.result) return <Empty>Run the agents to create approval items.</Empty>

  const decide = async (a, status) => {
    try { await api.decide(a.id, { status, reviewer, comment }); setComment(''); await onChange() } catch (e) { onError(e.message) }
  }
  const doExport = async () => {
    try { setExp(await api.exportZip(project.id, reviewer)); await onChange() } catch (e) { onError(e.message); setExp(null) }
  }
  const approved = approvals.filter((a) => a.status === 'approved').length
  return (
    <>
      <Section title="Human approval" right={<Badge tone={approved === approvals.length ? 'green' : 'amber'}>{approved}/{approvals.length} approved</Badge>}>
        <div className="card p-4 mb-4 grid gap-3 md:grid-cols-2">
          <label className="text-sm">Reviewer name (required)
            <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Your full name" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
          </label>
          <label className="text-sm">Comment (optional)
            <input value={comment} onChange={(e) => setComment(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
          </label>
        </div>
        <Table head={['Item', 'Type', 'Status', 'Reviewed by', 'Decision']}>
          {approvals.map((a) => (
            <tr key={a.id}>
              <td className="td"><b>{a.item_name}</b><div className="text-xs text-slate-500">{a.description}</div></td>
              <td className="td">{a.item_type}</td>
              <td className="td"><Badge tone={statusTone(a.status)}>{a.status}</Badge></td>
              <td className="td text-xs">{a.reviewer || '—'}<div className="text-slate-400">{a.comment}</div></td>
              <td className="td space-x-2 whitespace-nowrap">
                <button className="btn-ghost" disabled={!reviewer.trim()} onClick={() => decide(a, 'approved')}>Approve</button>
                <button className="btn-danger" disabled={!reviewer.trim()} onClick={() => decide(a, 'rejected')}>Reject</button>
              </td>
            </tr>
          ))}
        </Table>
      </Section>
      <Section title="Client approval documents">
        <a className="btn-ghost" href={api.packUrl(project.id)}>⬇ Download client approval pack (.docx)</a>
        <p className="mt-2 text-xs text-slate-500">Contains every claim with its source, calculations, privacy treatment, and a consent/sign-off page.</p>
      </Section>
      <Section title="Export">
        <button className="btn-primary" disabled={!reviewer.trim() || approved === 0} onClick={doExport}>Export approved items (.zip)</button>
        <p className="mt-2 text-xs text-slate-500">Only items a named reviewer has approved are exported. Raw evidence text and the approval pack are never included.</p>
        {exp && (
          <div className="mt-3 card p-4 text-sm">
            <a className="font-medium text-brand-700 underline" href={exp.download}>Download {exp.file}</a>
            {exp.excluded.length > 0 && <ul className="mt-2 list-disc pl-5 text-amber-700">{exp.excluded.map((e) => <li key={e}>Not exported — {e}</li>)}</ul>}
          </div>
        )}
      </Section>
      <Section title="Audit trail">
        <div className="card max-h-64 overflow-y-auto divide-y divide-slate-100 text-xs">
          {audit.map((l) => <div key={l.id} className="px-3 py-1.5"><span className="text-slate-400">{l.created_at}</span> · <b>{l.actor}</b> · {l.action} <span className="text-slate-500">{l.detail}</span></div>)}
        </div>
      </Section>
    </>
  )
}
