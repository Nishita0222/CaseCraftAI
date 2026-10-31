// Thin fetch wrapper. All calls go to the local FastAPI backend through the Vite proxy.
async function req(path, opts = {}) {
  const res = await fetch('/api' + path, opts)
  if (!res.ok) {
    let msg = res.statusText
    try { const j = await res.json(); msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail) } catch { /* ignore */ }
    throw new Error(msg)
  }
  return res.json()
}
const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const api = {
  health: () => req('/health'),
  projects: () => req('/projects'),
  createProject: (b) => req('/projects', json('POST', b)),
  project: (id) => req(`/projects/${id}`),
  deleteProject: (id) => req(`/projects/${id}`, { method: 'DELETE' }),
  demo: () => req('/demo', { method: 'POST' }),
  upload: (id, files) => {
    const fd = new FormData()
    for (const f of files) fd.append('files', f)
    return req(`/projects/${id}/documents`, { method: 'POST', body: fd })
  },
  deleteDocument: (id) => req(`/documents/${id}`, { method: 'DELETE' }),
  run: (id) => req(`/projects/${id}/run`, { method: 'POST' }),
  latestRun: (id) => req(`/projects/${id}/runs/latest`),
  approvals: (id) => req(`/projects/${id}/approvals`),
  decide: (aid, b) => req(`/approvals/${aid}/decision`, json('POST', b)),
  exportZip: (id, reviewer) => req(`/projects/${id}/export`, json('POST', { reviewer })),
  audit: (id) => req(`/projects/${id}/audit`),
  assetUrl: (pid, name, bust) => `/api/projects/${pid}/assets/${name}?v=${bust}`,
  packUrl: (pid) => `/api/projects/${pid}/approval-pack`,
}

import axios from "axios";

const API = axios.create({
    baseURL: "http://localhost:8000/api"
});

export const getCaseStudy = async () => {

    const response = await API.get("/case-study");

    return response.data;
};

export const exportWord = async (audience) => {

    const response = await API.post(
        `/export/${audience}`
    );

    return response.data;
};

export const downloadWord = async (filename) => {

    const response = await API.get(
        `/download/${filename}`,
        {
            responseType: "blob"
        }
    );

    const url = window.URL.createObjectURL(
        new Blob([response.data])
    );

    const link = document.createElement("a");

    link.href = url;
    link.setAttribute("download", filename);

    document.body.appendChild(link);

    link.click();

    link.remove();

    window.URL.revokeObjectURL(url);
};