export default function Header({ auth, onLogout }) {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white">
            <DocumentIcon />
          </div>
          <div>
            <h1 className="text-base font-semibold leading-tight text-slate-900">
              Document Summarizer
            </h1>
            <p className="text-xs text-slate-500">Google Drive · AI summaries</p>
          </div>
        </div>

        {auth.authenticated && (
          <div className="flex items-center gap-3">
            {auth.email && (
              <span className="hidden text-sm text-slate-600 sm:inline" title={auth.email}>
                {auth.email}
              </span>
            )}
            <button
              type="button"
              onClick={onLogout}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

function DocumentIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M7 4h7l4 4v11a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <path d="M14 4v4h4M9 13h6M9 16h6M9 10h2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}
