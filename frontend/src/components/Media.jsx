import React from 'react'
import { api } from '../api.js'
import { Badge, Cite, Empty, statusTone } from './ui.jsx'

export default function Media({ project, run, evMap, onCite }) {
  const assets = run?.result?.assets
  if (!assets) return <Empty>Run the agents to create media assets.</Empty>
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {assets.map((a) => (
        <figure key={a.name} className="card overflow-hidden">
          <img src={api.assetUrl(project.id, a.name, run.id)} alt={a.alt} className="w-full border-b border-slate-200 bg-white" />
          <figcaption className="p-3 text-sm">
            <div className="flex items-center gap-2"><b>{a.name}</b><Badge tone="teal">{a.type}</Badge><Badge tone={statusTone(a.status)}>{a.status.replace(/_/g, ' ')}</Badge></div>
            <p className="mt-1 text-slate-600">{a.caption}</p>
            <p className="mt-1 text-xs text-slate-500">Sources: {a.refs.map((r) => <Cite key={r} refId={r} evidence={evMap} onOpen={onCite} />)}</p>
          </figcaption>
        </figure>
      ))}
    </div>
  )
}
