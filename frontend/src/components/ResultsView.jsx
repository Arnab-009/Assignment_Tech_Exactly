import { useState } from 'react'
import { EXPORT_CSV_URL, EXPORT_PDF_URL } from '../api/client'

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

const STATUS_META = {
  success: { label: 'Summarized', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  empty: { label: 'Empty file', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  error: { label: 'Error', color: 'bg-red-50 text-red-700 border-red-200' },
}

function FileIcon({ mime }) {
  const meta = TYPE_META[mime]
  const c = meta?.iconColor || 'text-slate-400'
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className={`shrink-0 ${c}`} aria-hidden="true">
      <path d="M7 4h7l4 4v11a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M14 4v4h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

// ── Single-document focused result card ──────────────────────────────────────
function SingleDocResult({ item, elapsed }) {
  const [expanded, setExpanded] = useState(false)
  const typeMeta = TYPE_META[item.mime_type] || { label: item.mime_type, color: 'bg-slate-50 text-slate-700 border-slate-200' }
  const statusMeta = STATUS_META[item.status] || STATUS_META.error
  const summaryText = item.summary || item.error_message || 'No summary available.'
  const isLong = summaryText.length > 500
  const displayed = expanded || !isLong ? summaryText : summaryText.slice(0, 500) + '…'

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      {/* Status bar at the top */}
      <div className={`h-1.5 w-full ${item.status === 'success' ? 'bg-gradient-to-r from-emerald-400 to-emerald-500' : item.status === 'error' ? 'bg-gradient-to-r from-red-400 to-red-500' : 'bg-gradient-to-r from-amber-400 to-amber-500'}`} />

      <div className="p-6 sm:p-8">
        {/* File header */}
        <div className="flex flex-wrap items-start gap-3">
          <FileIcon mime={item.mime_type} />
          <div className="min-w-0 flex-1">
            {item.web_view_link ? (
              <a
                href={item.web_view_link}
                target="_blank"
                rel="noopener noreferrer"
                className="break-words text-lg font-bold text-blue-600 transition hover:text-blue-800 hover:underline"
              >
                {item.file_name}
              </a>
            ) : (
              <p className="break-words text-lg font-bold text-slate-900">{item.file_name}</p>
            )}
            <div className="mt-1.5 flex flex-wrap gap-2">
              <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${typeMeta.color}`}>
                {typeMeta.label}
              </span>
              <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${statusMeta.color}`}>
                {statusMeta.label}
              </span>
              {elapsed && (
                <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-[11px] font-medium text-slate-500">
                  ⏱ {elapsed}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="my-5 border-t border-slate-100" />

        {/* Summary label */}
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">AI Summary</p>

        {/* Summary text */}
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{displayed}</p>
        {isLong && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="mt-3 text-xs font-medium text-blue-600 transition hover:text-blue-800"
          >
            {expanded ? '▲ Show less' : '▼ Read more'}
          </button>
        )}
      </div>
    </div>
  )
}

// ── Main results view ────────────────────────────────────────────────────────
export default function ResultsView({ results, onBack }) {
  const elapsed = results.stats?.elapsed_seconds
    ? `${results.stats.elapsed_seconds.toFixed(1)}s`
    : null

  const single = results.summaries.length === 1 ? results.summaries[0] : null

  return (
    <div className="mx-auto max-w-2xl animate-fadeIn space-y-5">
      {/* Header row: Back + Download buttons */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-600
                     shadow-sm transition hover:bg-slate-50 hover:shadow"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M15 18l-6-6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Back to Files
        </button>

        <div className="ml-auto flex items-center gap-2">
          <a
            href={EXPORT_CSV_URL}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700
                       shadow-sm transition hover:bg-slate-50 hover:shadow"
          >
            <DownloadIcon />
            Download CSV
          </a>
          <a
            href={EXPORT_PDF_URL}
            className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-3.5 py-2 text-xs font-semibold text-white
                       shadow-sm transition hover:from-blue-700 hover:to-indigo-700 hover:shadow"
          >
            <DownloadIcon />
            Download PDF
          </a>
        </div>
      </div>

      {/* Single doc result */}
      {single && <SingleDocResult item={single} elapsed={elapsed} />}

      {/* Fallback: multi-doc table (shouldn't normally appear in this flow) */}
      {!single && (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80">
                  <th className="py-3 pl-5 pr-2 text-center text-[11px] font-semibold uppercase tracking-wider text-slate-400">#</th>
                  <th className="px-3 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">File</th>
                  <th className="hidden px-3 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400 sm:table-cell">Type</th>
                  <th className="px-3 py-3 pr-5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Summary</th>
                </tr>
              </thead>
              <tbody>
                {results.summaries.map((item, i) => (
                  <MultiRow key={item.file_id} item={item} index={i + 1} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function MultiRow({ item, index }) {
  const [expanded, setExpanded] = useState(false)
  const typeMeta = TYPE_META[item.mime_type] || { label: item.mime_type, color: 'bg-slate-50 text-slate-700 border-slate-200' }
  const text = item.summary || item.error_message || 'No summary.'
  const isLong = text.length > 200
  const displayed = expanded || !isLong ? text : text.slice(0, 200) + '…'
  return (
    <tr className="border-b border-slate-100 last:border-0 hover:bg-slate-50/60">
      <td className="py-4 pl-5 pr-2 text-center text-xs font-medium text-slate-400">{index}</td>
      <td className="px-3 py-4">
        <div className="flex items-center gap-2">
          <FileIcon mime={item.mime_type} />
          <span className="truncate text-sm font-medium text-slate-800" title={item.file_name}>{item.file_name}</span>
        </div>
      </td>
      <td className="hidden px-3 py-4 sm:table-cell">
        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${typeMeta.color}`}>{typeMeta.label}</span>
      </td>
      <td className="px-3 py-4 pr-5">
        <p className="text-sm leading-relaxed text-slate-600">{displayed}</p>
        {isLong && (
          <button type="button" onClick={() => setExpanded(v => !v)} className="mt-1 text-xs font-medium text-blue-600 hover:text-blue-800">
            {expanded ? '▲ Show less' : '▼ Read more'}
          </button>
        )}
      </td>
    </tr>
  )
}

function DownloadIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 3v12m0 0-4-4m4 4 4-4M5 21h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

