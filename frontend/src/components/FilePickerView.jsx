import { useEffect, useState } from 'react'
import { api } from '../api/client'
import Spinner from './Spinner'

const TYPE_META = {
  'application/pdf': { label: 'PDF', color: 'bg-red-50 text-red-700 border-red-200', iconColor: 'text-red-500' },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
    label: 'DOCX', color: 'bg-blue-50 text-blue-700 border-blue-200', iconColor: 'text-blue-500',
  },
  'text/plain': { label: 'TXT', color: 'bg-amber-50 text-amber-700 border-amber-200', iconColor: 'text-amber-500' },
  'application/vnd.google-apps.document': {
    label: 'Google Doc', color: 'bg-emerald-50 text-emerald-700 border-emerald-200', iconColor: 'text-emerald-500',
  },
}

function formatSize(bytes) {
  if (!bytes) return null
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function FileIcon({ mime, className = '' }) {
  const meta = TYPE_META[mime]
  const color = meta?.iconColor || 'text-slate-400'
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className={`shrink-0 ${color} ${className}`} aria-hidden="true">
      <path d="M7 4h7l4 4v11a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M14 4v4h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

export default function FilePickerView({ folder, onBack, onSummarize, busy }) {
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState(null)
  const [selectedFileId, setSelectedFileId] = useState(null)

  useEffect(() => {
    setLoading(true)
    setFetchError(null)
    api.listFiles(folder.id)
      .then((data) => {
        setFiles(data)
        if (data.length === 1) setSelectedFileId(data[0].id)
      })
      .catch(() => setFetchError('Could not load files from this folder.'))
      .finally(() => setLoading(false))
  }, [folder.id])

  const handleSummarize = () => {
    if (selectedFileId && !busy) {
      onSummarize(folder.id, selectedFileId)
    }
  }

  return (
    <div className="mx-auto max-w-2xl animate-fadeIn">
      {/* Back + title */}
      <div className="mb-6 flex items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-600
                     shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M15 18l-6-6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Back to Folders
        </button>
        <div className="min-w-0">
          <h2 className="truncate text-lg font-bold text-slate-900">{folder.name}</h2>
          <p className="text-xs text-slate-400">Select a document to summarize</p>
        </div>
      </div>

      {/* File list card */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-400">
            <Spinner />
            <span>Loading files…</span>
          </div>
        ) : fetchError ? (
          <p className="py-12 text-center text-sm text-red-500">{fetchError}</p>
        ) : files.length === 0 ? (
          <div className="py-14 text-center">
            <p className="text-sm font-medium text-slate-600">No supported files found</p>
            <p className="mt-1 text-xs text-slate-400">This folder has no PDF, DOCX, TXT, or Google Doc files.</p>
          </div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {files.map((file) => {
              const meta = TYPE_META[file.mime_type] || { label: file.mime_type, color: 'bg-slate-50 text-slate-700 border-slate-200', iconColor: 'text-slate-400' }
              const isSelected = selectedFileId === file.id
              const sizeLabel = formatSize(file.size)

              return (
                <li key={file.id}>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => setSelectedFileId(file.id)}
                    className={`w-full px-5 py-4 text-left transition focus:outline-none first:rounded-t-2xl last:rounded-b-2xl
                      ${isSelected
                        ? 'bg-blue-50 ring-2 ring-inset ring-blue-500'
                        : 'hover:bg-slate-50'
                      } disabled:opacity-60`}
                  >
                    <div className="flex items-center gap-3">
                      {/* Radio indicator */}
                      <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2
                        ${isSelected ? 'border-blue-600 bg-blue-600' : 'border-slate-300 bg-white'}`}>
                        {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
                      </span>

                      {/* File icon */}
                      <FileIcon mime={file.mime_type} />

                      {/* File info */}
                      <div className="min-w-0 flex-1">
                        <p className={`truncate text-sm font-medium ${isSelected ? 'text-blue-900' : 'text-slate-800'}`}>
                          {file.file_name ?? file.name}
                        </p>
                        {sizeLabel && (
                          <p className="mt-0.5 text-xs text-slate-400">{sizeLabel}</p>
                        )}
                      </div>

                      {/* Type badge */}
                      <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${meta.color}`}>
                        {meta.label}
                      </span>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      {/* Summarize button */}
      {!loading && !fetchError && files.length > 0 && (
        <button
          type="button"
          onClick={handleSummarize}
          disabled={!selectedFileId || busy}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-3
                     text-sm font-semibold text-white shadow-md shadow-blue-200
                     transition-all duration-200
                     hover:from-blue-700 hover:to-indigo-700 hover:shadow-lg hover:shadow-blue-300
                     disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          {busy ? (
            <>
              <Spinner light />
              <span>Summarizing…</span>
            </>
          ) : (
            <>
              <SparklesIcon />
              <span>
                {selectedFileId
                  ? `Summarize "${files.find(f => f.id === selectedFileId)?.name ?? 'file'}"`
                  : 'Select a file to summarize'}
              </span>
            </>
          )}
        </button>
      )}
    </div>
  )
}

function SparklesIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48 2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48 2.83-2.83"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}
