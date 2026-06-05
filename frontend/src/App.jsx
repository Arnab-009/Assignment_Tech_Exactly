import { useCallback, useEffect, useState } from 'react'
import { api } from './api/client'
import Header from './components/Header'
import Alert from './components/Alert'
import Spinner from './components/Spinner'
import ConnectCard from './components/ConnectCard'
import HomeView from './components/HomeView'
import FilePickerView from './components/FilePickerView'
import ResultsView from './components/ResultsView'

const AUTH_ERROR_MESSAGES = {
  invalid_state: 'Login session expired or could not be verified. Please try again.',
  token_exchange_failed: 'Could not complete Google sign-in. Please try again.',
  missing_code: 'Google did not return an authorization code. Please try again.',
  access_denied: 'You declined the Google permission request.',
}

export default function App() {
  const [auth, setAuth] = useState({
    loading: true,
    authenticated: false,
    email: null,
    defaultFolderId: '',
  })
  const [selectedFolder, setSelectedFolder] = useState(null) // { id, name }
  const [results, setResults] = useState(null)
  const [summarizing, setSummarizing] = useState(false)
  const [error, setError] = useState(null)

  const refreshAuth = useCallback(async () => {
    try {
      const status = await api.getAuthStatus()
      setAuth({
        loading: false,
        authenticated: status.authenticated,
        email: status.email,
        defaultFolderId: status.default_folder_id || '',
      })
    } catch {
      setAuth({ loading: false, authenticated: false, email: null, defaultFolderId: '' })
    }
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const authError = params.get('auth_error')
    if (authError) {
      setError(AUTH_ERROR_MESSAGES[authError] || 'Authentication failed. Please try again.')
      window.history.replaceState({}, '', window.location.pathname)
    }
    refreshAuth()
  }, [refreshAuth])

  const handleFolderSelect = (folder) => {
    setSelectedFolder(folder)
    setResults(null)
    setError(null)
  }

  const handleSummarize = async (folderId, fileId) => {
    setError(null)
    setSummarizing(true)
    try {
      const data = await api.summarize(folderId, fileId)
      setResults(data)
    } catch (err) {
      if (err.status === 401) {
        setAuth((prev) => ({ ...prev, authenticated: false }))
        setError('Your session expired. Please reconnect Google Drive.')
      } else {
        setError(err.message)
      }
    } finally {
      setSummarizing(false)
    }
  }

  const handleBackToFiles = () => {
    setResults(null)
    setError(null)
  }

  const handleBackToFolders = () => {
    setSelectedFolder(null)
    setResults(null)
    setError(null)
  }

  const handleLogout = async () => {
    try {
      await api.logout()
    } catch {
      /* ignore */
    }
    setSelectedFolder(null)
    setResults(null)
    setAuth((prev) => ({ ...prev, authenticated: false, email: null }))
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <Header auth={auth} onLogout={handleLogout} />
      <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:py-10">
        {error && (
          <Alert variant="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {auth.loading ? (
          <div className="flex justify-center py-24">
            <Spinner label="Loading…" />
          </div>
        ) : !auth.authenticated ? (
          <ConnectCard />
        ) : results ? (
          <ResultsView
            results={results}
            onBack={handleBackToFiles}
          />
        ) : selectedFolder ? (
          <FilePickerView
            folder={selectedFolder}
            onBack={handleBackToFolders}
            onSummarize={handleSummarize}
            busy={summarizing}
          />
        ) : (
          <HomeView
            defaultFolderId={auth.defaultFolderId}
            onSubmit={handleFolderSelect}
          />
        )}
      </main>
      <footer className="pb-10 pt-4 text-center text-xs text-slate-400">
        Document Summarizer · FastAPI · Gemini 2.5 Flash · React
      </footer>
    </div>
  )
}
