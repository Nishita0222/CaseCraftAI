import React from 'react'

const TONES = {
  green: 'bg-emerald-100 text-emerald-800', amber: 'bg-amber-100 text-amber-800', red: 'bg-rose-100 text-rose-800',
  slate: 'bg-slate-100 text-slate-700', blue: 'bg-sky-100 text-sky-800', teal: 'bg-brand-100 text-brand-700',
}
export const Badge = ({ tone = 'slate', children }) => (
  <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>{children}</span>
)

export const statusTone = (s) => ({
  verified: 'green', conflict_resolved: 'blue', unresolved: 'red', estimate_only: 'amber', privacy_blocked: 'red',
  approved: 'green', rejected: 'red', pending: 'amber', ready_for_review: 'teal', blocked: 'red',
  done: 'green', running: 'blue', failed: 'red', completed: 'green', queued: 'slate',
}[s] || 'slate')

export const Empty = ({ children }) => (
  <div className="card p-10 text-center text-slate-500 text-sm">{children}</div>
)

export const Section = ({ title, right, children }) => (
  <div className="mb-6">
    <div className="flex items-center justify-between mb-2">
      <h2 className="font-semibold text-slate-800">{title}</h2>{right}
    </div>
    {children}
  </div>
)

/** Evidence citation chip. Hover shows the source sentence; click jumps to the Evidence tab. */
export function Cite({ refId, evidence, onOpen }) {
  const e = evidence?.[refId]
  return (
    <button
      onClick={() => onOpen?.(refId)}
      title={e ? `${e.doc} @ ${e.location}\n${e.text}` : refId}
      className="mx-0.5 rounded bg-brand-100 px-1.5 py-0.5 text-xs font-mono text-brand-700 hover:bg-brand-500 hover:text-white"
    >{refId}</button>
  )
}

export const Table = ({ head, children }) => (
  <div className="card overflow-x-auto">
    <table className="w-full">
      <thead><tr>{head.map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
      <tbody>{children}</tbody>
    </table>
  </div>
)
