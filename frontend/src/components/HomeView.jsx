import { useState } from 'react'
import Spinner from './Spinner'

export default function HomeView({ defaultFolderId, onSubmit, busy }) {
  const [folderId, setFolderId] = useState(defaultFolderId || '')
  const isValid = folderId.trim().length >= 10

  const handleSubmit = (e) => {
    e.preventDefault()
    if (isValid && !busy) onSubmit(folderId.trim())
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
          Enter a Google Drive folder ID to scan its documents. The AI will read
          each PDF, DOCX, and TXT file and produce a concise summary.
        </p>
      </div>

      {/* Form card */}
      <form
        onSubmit={handleSubmit}
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"
      >
        <label
          htmlFor="folderId"
          className="mb-2 block text-sm font-medium text-slate-700"
        >
          Google Drive Folder ID
        </label>
        <div className="relative">
          <input
            id="folderId"
            type="text"
            value={folderId}
            onChange={(e) => setFolderId(e.target.value)}
            placeholder="e.g. 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
            disabled={busy}
            className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-800
                       placeholder:text-slate-400
                       focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100
                       disabled:opacity-60"
          />
          {folderId && (
            <button
              type="button"
              onClick={() => setFolderId('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 transition hover:text-slate-600"
              aria-label="Clear input"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          )}
        </div>

        <p className="mt-2 text-xs text-slate-400">
          Paste the folder ID from the URL:&nbsp;
          <code className="rounded bg-slate-100 px-1 py-0.5 text-[11px] text-slate-500">
            drive.google.com/drive/folders/<strong>{'<ID>'}</strong>
          </code>
        </p>

        <button
          type="submit"
          disabled={!isValid || busy}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-3
                     text-sm font-semibold text-white shadow-md shadow-blue-200
                     transition-all duration-200
                     hover:from-blue-700 hover:to-indigo-700 hover:shadow-lg hover:shadow-blue-300
                     disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          {busy ? (
            <>
              <Spinner light />
              <span>Summarizing documents…</span>
            </>
          ) : (
            <>
              <SparklesIcon />
              <span>Summarize Documents</span>
            </>
          )}
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
