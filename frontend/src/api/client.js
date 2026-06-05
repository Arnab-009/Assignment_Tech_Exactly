// Thin fetch wrapper around the backend API.
//
// All requests use relative URLs (so the same build works behind the Vite dev
// proxy and the production nginx proxy) and `credentials: 'include'` so the
// session cookie is always sent.

const JSON_HEADERS = { 'Content-Type': 'application/json' }

async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'include',
    headers: { ...JSON_HEADERS, ...(options.headers || {}) },
    ...options,
  })

  if (response.status === 204) return null

  const text = await response.text()
  let payload = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = { detail: text }
    }
  }

  if (!response.ok) {
    const message =
      (payload && payload.detail) || `Request failed (${response.status})`
    const error = new Error(message)
    error.status = response.status
    error.payload = payload
    throw error
  }
  return payload
}

export const api = {
  getAuthStatus: () => request('/api/auth/status'),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  listFolders: () => request('/api/drive/folders'),
  listFiles: (folderId) =>
    request(`/api/drive/files?folder_id=${encodeURIComponent(folderId)}`),
  summarize: (folderId, fileId = null) =>
    request('/api/summarize', {
      method: 'POST',
      body: JSON.stringify({
        folder_id: folderId,
        ...(fileId ? { file_id: fileId } : {}),
      }),
    }),
  getResults: () => request('/api/results'),
}

export const LOGIN_URL = '/api/auth/login'
export const EXPORT_CSV_URL = '/api/export/csv'
export const EXPORT_PDF_URL = '/api/export/pdf'
