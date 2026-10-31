import React, { useRef, useState } from 'react'
import { api } from '../api.js'
import { Badge, Empty, Section } from './ui.jsx'

export default function Documents({ project, onChange, onError }) {
  const input = useRef()
  const [drag, setDrag] = useState(false)
  const [busy, setBusy] = useState(false)

  const upload = async (files) => {
    if (!files?.length) return
    setBusy(true)
    try { await api.upload(project.id, files); await onChange() } catch (e) { onError(e.message) } finally { setBusy(false) }
  }
  const docs = project.documents || []
  return (
    <Section title="Project documents">
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files) }}
        onClick={() => input.current.click()}
        className={`card cursor-pointer border-2 border-dashed p-8 text-center text-sm transition ${drag ? 'border-brand-500 bg-brand-50' : 'border-slate-300'}`}
      >
        <input ref={input} type="file" multiple hidden accept=".pdf,.docx,.xlsx,.xlsm,.eml,.txt,.md,.csv"
               onChange={(e) => upload(e.target.files)} />
        <p className="font-medium">{busy ? 'Uploading…' : 'Drop files here or click to browse'}</p>
        <p className="text-slate-500 mt-1">PDF · DOCX · XLSX · EML · TXT · CSV — stored only on this computer</p>
      </div>
      <div className="mt-4">
        {docs.length === 0 ? <Empty>No documents yet.</Empty> : (
          <ul className="card divide-y divide-slate-100">
            {docs.map((d) => (
              <li key={d.id} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                <Badge tone="teal">{d.kind}</Badge>
                <span className="flex-1 truncate">{d.filename}</span>
                <span className="text-slate-400">{(d.size / 1024).toFixed(1)} KB</span>
                <button className="text-rose-600 hover:underline" onClick={async () => { await api.deleteDocument(d.id); onChange() }}>remove</button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Section>
  )
}
