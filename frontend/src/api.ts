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

async function fetchData(url: string, method: string = 'GET', body: any = null) {
  const options: RequestInit = {
    method,
    headers: {
      ...authHeaders(),
      'Content-Type': 'application/json',
    },
  };
  if (body) {
    options.body = JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE}${url}`, options);
  if (!res.ok) {
    let errorMsg = `${res.status}: ${res.statusText}`;
    try {
      const errorData = await res.json();
      errorMsg = errorData.message || errorMsg;
    } catch (e) {
      // Ignore if JSON parsing fails
    }
    throw new Error(errorMsg);
  }
  return res.json();
}

export const api = {
  acts: () => fetchData('/acts'),
  tree: (act: string) => fetchData(`/tree/${act}`),
  generateMcpToken: () => fetchData('/mcp-token', 'POST'),
  listMcpTokens: () => fetchData('/mcp-tokens'),
  revokeMcpToken: (token: string) => fetchData(`/mcp-tokens/${token}/revoke`, 'POST'),
  section: (act: string, section: string) => fetchJson(`/section/${act}/${section}`),
  commentary: (act: string, section: string) => fetchJson(`/commentary/${act}/${section}`),
  cases: (act: string, section: string) => fetchJson(`/cases/${act}/${section}`),
  rulings: (act: string, section: string) => fetchJson(`/rulings/${act}/${section}`),
  definitions: (act: string) => fetchJson(`/definitions/${act}`),
  definition: (act: string, term: string) => fetchJson(`/definition/${act}/${term}`),
  definitionText: (act: string, term: string) => fetchJson(`/definition-text/${act}/${term}`),
  search: (q: string, act?: string, offset?: number, limit?: number) => {
    let url = `/search?q=${encodeURIComponent(q)}`
    if (act) url += `&act=${act}`
    if (offset !== undefined) url += `&offset=${offset}`
    if (limit !== undefined) url += `&limit=${limit}`
    return fetchJson(url)
  },
  ruling: (citation: string) => fetchJson(`/ruling/${encodeURIComponent(citation)}`),
  rulingSections: (citation: string) => fetchJson(`/ruling-sections/${encodeURIComponent(citation)}`),
  listComments: (act: string, section: string) => fetchJson(`/comments/${act}/${section}`),
  createComment: (act: string, section: string, author: string, text: string) =>
    fetchData('/comments', 'POST', { act, section, author, text }),
  resolveComment: (commentId: number) =>
    fetchData('/comments/resolve', 'POST', { comment_id: commentId }),
  searchFlat: (q: string, limit?: number) => {
    let url = `/search/flat?q=${encodeURIComponent(q)}`
    if (limit !== undefined) url += `&limit=${limit}`
    return fetchJson(url)
  },
  info: () => fetchJson('/info'),
  sectionRefs: (act: string, section: string) => fetchJson(`/section-refs/${act}/${section}`),
}
