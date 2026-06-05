import { useState } from 'react'
import { EXPORT_CSV_URL, EXPORT_PDF_URL } from '../api/client'

// ── Friendly MIME-type → label + color ───────────────────────────────────────
const TYPE_META = {
  'application/pdf': { label: 'PDF', color: 'bg-red-50 text-red-700 border-red-200' },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
    label: 'DOCX',
    color: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  'text/plain': { label: 'TXT', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  'application/vnd.google-apps.document': {
    label: 'Google Doc',
    color: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  },
}

const STATUS_META = {
  success: { label: 'Summarized', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  empty: { label: 'Empty', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  error: { label: 'Error', color: 'bg-red-50 text-red-700 border-red-200' },
}

function Badge({ meta }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${meta.color}`}
    >
      {meta.label}
    </span>
  )
}

// ── Stats bar ────────────────────────────────────────────────────────────────
function StatsBar({ stats }) {
  const items = [
    { label: 'Total Files', value: stats.total, icon: '📄', accent: 'from-slate-500 to-slate-600' },
    { label: 'Summarized', value: stats.success, icon: '✅', accent: 'from-emerald-500 to-emerald-600' },
    { label: 'Empty', value: stats.empty, icon: '📭', accent: 'from-amber-500 to-amber-600' },
    { label: 'Errors', value: stats.error, icon: '❌', accent: 'from-red-500 to-red-600' },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {items.map((item) => (
        <div
          key={item.label}
          className="group relative overflow-hidden rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md"
        >
          <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${item.accent}`} />
          <p className="text-xs font-medium text-slate-500">{item.label}</p>
          <p className="mt-1 text-2xl font-bold text-slate-800">{item.value}</p>
          <span className="absolute right-3 top-3 text-lg opacity-50">{item.icon}</span>
        </div>
      ))}
    </div>
  )
}

// ── Single summary row (expandable) ──────────────────────────────────────────
function SummaryRow({ item, index }) {
  const [expanded, setExpanded] = useState(false)
  const typeMeta = TYPE_META[item.mime_type] || { label: item.mime_type, color: 'bg-slate-50 text-slate-700 border-slate-200' }
  const statusMeta = STATUS_META[item.status] || STATUS_META.error

  const summaryText = item.summary || item.error_message || 'No summary available.'
  const isLong = summaryText.length > 280
  const displayed = expanded || !isLong ? summaryText : summaryText.slice(0, 280) + '…'

  return (
    <tr className="group border-b border-slate-100 transition last:border-0 hover:bg-slate-50/60">
      {/* Index */}
      <td className="py-4 pl-5 pr-2 text-center text-xs font-medium text-slate-400">
        {index}
      </td>

      {/* File name + link */}
      <td className="px-3 py-4">
        <div className="flex items-center gap-2">
          <FileIcon mime={item.mime_type} />
          <div className="min-w-0">
            {item.web_view_link ? (
              <a
                href={item.web_view_link}
                target="_blank"
                rel="noopener noreferrer"
                className="block truncate text-sm font-medium text-blue-600 transition hover:text-blue-800 hover:underline"
                title={item.file_name}
              >
                {item.file_name}
              </a>
            ) : (
              <span className="block truncate text-sm font-medium text-slate-800" title={item.file_name}>
                {item.file_name}
              </span>
            )}
          </div>
        </div>
      </td>

      {/* Type badge */}
      <td className="hidden px-3 py-4 sm:table-cell">
        <Badge meta={typeMeta} />
      </td>

      {/* Status badge */}
      <td className="hidden px-3 py-4 md:table-cell">
        <Badge meta={statusMeta} />
      </td>

      {/* Summary */}
      <td className="px-3 py-4 pr-5">
        <p className="text-sm leading-relaxed text-slate-600">
          {displayed}
        </p>
        {isLong && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="mt-1 text-xs font-medium text-blue-600 transition hover:text-blue-800"
          >
            {expanded ? '▲ Show less' : '▼ Read more'}
          </button>
        )}
      </td>
    </tr>
  )
}

// ── File icon by MIME type ───────────────────────────────────────────────────
function FileIcon({ mime }) {
  const colors = {
    'application/pdf': 'text-red-500',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'text-blue-500',
    'text/plain': 'text-amber-500',
    'application/vnd.google-apps.document': 'text-emerald-500',
  }
  const c = colors[mime] || 'text-slate-400'

  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className={`shrink-0 ${c}`} aria-hidden="true">
      <path
        d="M7 4h7l4 4v11a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path d="M14 4v4h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

// ── Main results view ────────────────────────────────────────────────────────
export default function ResultsView({ results, onReset }) {
  const elapsed = results.stats?.elapsed_seconds
    ? `${results.stats.elapsed_seconds.toFixed(1)}s`
    : null

  return (
    <div className="animate-fadeIn space-y-6">
      {/* Page header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900 sm:text-2xl">Summary Results</h2>
          {elapsed && (
            <p className="mt-0.5 text-xs text-slate-400">
              Completed in {elapsed} · Folder&nbsp;
              <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-500">
                {results.folder_id}
              </code>
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <a
            href={EXPORT_CSV_URL}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 hover:shadow"
          >
            <DownloadIcon />
            CSV
          </a>
          <a
            href={EXPORT_PDF_URL}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 hover:shadow"
          >
            <DownloadIcon />
            PDF
          </a>
          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:from-blue-700 hover:to-indigo-700 hover:shadow"
          >
            <RefreshIcon />
            Run Again
          </button>
        </div>
      </div>

      {/* Stats */}
      <StatsBar stats={results.stats} />

      {/* Summary table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80">
                <th className="py-3 pl-5 pr-2 text-center text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  #
                </th>
                <th className="px-3 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  File Name
                </th>
                <th className="hidden px-3 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400 sm:table-cell">
                  Type
                </th>
                <th className="hidden px-3 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400 md:table-cell">
                  Status
                </th>
                <th className="px-3 py-3 pr-5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Summary
                </th>
              </tr>
            </thead>
            <tbody>
              {results.summaries.map((item, i) => (
                <SummaryRow key={item.file_id} item={item} index={i + 1} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ── Tiny SVG icons ───────────────────────────────────────────────────────────
function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 3v12m0 0-4-4m4 4 4-4M5 21h14"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function RefreshIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M1 4v6h6M23 20v-6h-6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4-4.64 4.36A9 9 0 0 1 3.51 15"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
