const API_BASE = '/api'

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('bearer_token') || ''
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function fetchJson(path: string) {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`)
  return res.json()
}

export const api = {
  acts: () => fetchJson('/acts'),
  tree: (act: string) => fetchJson(`/tree/${act}`),
  section: (act: string, section: string) => fetchJson(`/section/${act}/${section}`),
  definitions: (act: string) => fetchJson(`/definitions/${act}`),
  definition: (act: string, term: string) => fetchJson(`/definition/${act}/${term}`),
  search: (q: string, act?: string) => fetchJson(`/search?q=${encodeURIComponent(q)}${act ? `&act=${act}` : ''}`),
}
