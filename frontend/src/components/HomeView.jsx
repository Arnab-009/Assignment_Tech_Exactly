import { useEffect, useState } from 'react'
import { api } from '../api/client'
import Spinner from './Spinner'

export default function HomeView({ defaultFolderId, onSubmit }) {
  const [folderId, setFolderId] = useState(defaultFolderId || '')
  const [folders, setFolders] = useState([])
  const [loadingFolders, setLoadingFolders] = useState(true)
  const [folderError, setFolderError] = useState(null)

  const isValid = folderId.trim().length >= 10

  useEffect(() => {
    api.listFolders()
      .then((data) => {
        setFolders(data)
        if (!defaultFolderId && data.length > 0) {
          setFolderId(data[0].id)
        }
      })
      .catch(() => setFolderError('Could not load folders from Google Drive.'))
      .finally(() => setLoadingFolders(false))
  }, [defaultFolderId])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!isValid) return
    const folder = folders.find((f) => f.id === folderId)
    onSubmit({ id: folderId, name: folder?.name || folderId })
  }

  return (
    <div className="mx-auto max-w-2xl animate-fadeIn">
      {/* Hero section */}
      <div className="mb-8 text-center">
        <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-200">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"
              stroke="#fff"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
            <rect x="9" y="3" width="6" height="4" rx="1" stroke="#fff" strokeWidth="1.6" />
            <path d="M9 12h6M9 16h4" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-slate-900 sm:text-3xl">
          Summarize your documents
        </h2>
        <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-slate-500">
          Select a Google Drive folder to browse its documents and pick one to
          summarize with AI.
        </p>
      </div>

      {/* Form card */}
      <form
        onSubmit={handleSubmit}
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"
      >
        <label
          htmlFor="folderSelect"
          className="mb-2 block text-sm font-medium text-slate-700"
        >
          Google Drive Folder
        </label>

        {loadingFolders ? (
          <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-400">
            <Spinner />
            <span>Loading folders…</span>
          </div>
        ) : folderError ? (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {folderError}
          </p>
        ) : folders.length === 0 ? (
          <p className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-400">
            No folders found in your Google Drive.
          </p>
        ) : (
          <div className="relative">
            <select
              id="folderSelect"
              value={folderId}
              onChange={(e) => setFolderId(e.target.value)}
              disabled={loadingFolders}
              className="w-full appearance-none rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 pr-10 text-sm text-slate-800
                         focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100
                         disabled:opacity-60"
            >
              <option value="" disabled>Select a folder…</option>
              {folders.map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
            {/* Custom chevron */}
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
          </div>
        )}

        <button
          type="submit"
          disabled={!isValid || loadingFolders}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-3
                     text-sm font-semibold text-white shadow-md shadow-blue-200
                     transition-all duration-200
                     hover:from-blue-700 hover:to-indigo-700 hover:shadow-lg hover:shadow-blue-300
                     disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          <FolderIcon />
          <span>Browse Files</span>
          <ChevronRightIcon />
        </button>
      </form>

      {/* Feature pills */}
      <div className="mt-6 flex flex-wrap justify-center gap-3 text-xs text-slate-400">
        {['PDF', 'DOCX', 'TXT', 'Google Docs'].map((type) => (
          <span
            key={type}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 shadow-sm"
          >
            {type}
          </span>
        ))}
      </div>
    </div>
  )
}

function FolderIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  )
}

function ChevronRightIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
