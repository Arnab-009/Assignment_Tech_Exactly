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
  success: { label: 'Analyzed', color: 'bg-emerald-50 text-emerald-700 border-emerald-200', bar: 'from-emerald-400 to-emerald-500' },
  empty: { label: 'Empty file', color: 'bg-amber-50 text-amber-700 border-amber-200', bar: 'from-amber-400 to-amber-500' },
  error: { label: 'Error', color: 'bg-red-50 text-red-700 border-red-200', bar: 'from-red-400 to-red-500' },
}

const QUALITY_COLOR = {
  High: 'text-emerald-600',
  Medium: 'text-amber-600',
  Low: 'text-red-500',
}

// ── Small building blocks ────────────────────────────────────────────────────
function FileIcon({ mime }) {
  const c = TYPE_META[mime]?.iconColor || 'text-slate-400'
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className={`shrink-0 ${c}`} aria-hidden="true">
      <path d="M7 4h7l4 4v11a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M14 4v4h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

function Badge({ className = '', children }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${className}`}>
      {children}
    </span>
  )
}

function SectionLabel({ children }) {
  return <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{children}</p>
}

function Metric({ label, value, accent }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2.5 text-center">
      <p className={`text-lg font-bold leading-tight ${accent || 'text-slate-800'}`}>{value}</p>
      <p className="mt-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-400">{label}</p>
    </div>
  )
}

function EntityGroup({ label, items, color }) {
  if (!items || items.length === 0) return null
  return (
    <div>
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((it, i) => (
          <span key={i} className={`rounded-md border px-2 py-0.5 text-xs font-medium ${color}`}>{it}</span>
        ))}
      </div>
    </div>
  )
}

// ── The main intelligence card ───────────────────────────────────────────────
function IntelligenceCard({ item, elapsed }) {
  const [expanded, setExpanded] = useState(false)
  const typeMeta = TYPE_META[item.mime_type] || { label: item.file_type || 'File', color: 'bg-slate-50 text-slate-700 border-slate-200' }
  const statusMeta = STATUS_META[item.status] || STATUS_META.error
  const isSuccess = item.status === 'success'

  const summaryText = item.summary || item.error_message || 'No summary available.'
  const isLong = summaryText.length > 600
  const displayed = expanded || !isLong ? summaryText : summaryText.slice(0, 600) + '…'

  const entities = item.entities || {}
  const hasEntities =
    (entities.organizations?.length || entities.monetary_values?.length || entities.percentages?.length ||
      entities.dates?.length || entities.locations?.length) > 0

  const confidencePct = item.confidence ? Math.round(item.confidence * 100) : null

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className={`h-1.5 w-full bg-gradient-to-r ${statusMeta.bar}`} />

      <div className="p-6 sm:p-8">
        {/* Header */}
        <div className="flex flex-wrap items-start gap-3">
          <FileIcon mime={item.mime_type} />
          <div className="min-w-0 flex-1">
            {item.web_view_link ? (
              <a href={item.web_view_link} target="_blank" rel="noopener noreferrer"
                className="break-words text-lg font-bold text-blue-600 transition hover:text-blue-800 hover:underline">
                {item.file_name}
              </a>
            ) : (
              <p className="break-words text-lg font-bold text-slate-900">{item.file_name}</p>
            )}
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge className={typeMeta.color}>{typeMeta.label}</Badge>
              {isSuccess && item.document_category && (
                <Badge className="border-indigo-200 bg-indigo-50 text-indigo-700">🏷 {item.document_category}</Badge>
              )}
              <Badge className={statusMeta.color}>{statusMeta.label}</Badge>
              {elapsed && (
                <Badge className="border-slate-200 bg-slate-50 text-slate-500">⏱ {elapsed}</Badge>
              )}
            </div>
          </div>
        </div>

        {!isSuccess ? (
          <p className="mt-5 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600">{summaryText}</p>
        ) : (
          <>
            {/* Metrics */}
            <div className="mt-6 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
              <Metric label="Pages" value={item.pages ?? '—'} />
              <Metric label="Words" value={(item.word_count || 0).toLocaleString()} />
              <Metric label="Tables" value={item.tables_found || 0} accent={item.tables_found ? 'text-blue-600' : undefined} />
              <Metric
                label={`Confidence${item.document_quality ? ` · ${item.document_quality}` : ''}`}
                value={confidencePct != null ? `${confidencePct}%` : '—'}
                accent={QUALITY_COLOR[item.document_quality]}
              />
            </div>

            {/* Key topics */}
            {item.key_topics?.length > 0 && (
              <div className="mt-6">
                <SectionLabel>Key Topics</SectionLabel>
                <div className="flex flex-wrap gap-2">
                  {item.key_topics.map((topic, i) => (
                    <span key={i} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-100">
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Important numbers */}
            {item.important_numbers?.length > 0 && (
              <div className="mt-6">
                <SectionLabel>Important Numbers</SectionLabel>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {item.important_numbers.map((num, i) => (
                    <div key={i} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-gradient-to-br from-slate-50 to-white px-3 py-2">
                      <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                      <span className="text-sm font-medium text-slate-700">{num}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Table insights */}
            {item.table_insights && (
              <div className="mt-6">
                <SectionLabel>Table Insights</SectionLabel>
                <div className="rounded-lg border-l-4 border-indigo-400 bg-indigo-50/60 px-4 py-3 text-sm leading-relaxed text-slate-700">
                  📊 {item.table_insights}
                </div>
              </div>
            )}

            {/* Summary */}
            <div className="mt-6">
              <SectionLabel>Executive Summary</SectionLabel>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{displayed}</p>
              {isLong && (
                <button type="button" onClick={() => setExpanded((v) => !v)}
                  className="mt-3 text-xs font-medium text-blue-600 transition hover:text-blue-800">
                  {expanded ? '▲ Show less' : '▼ Read more'}
                </button>
              )}
            </div>

            {/* Entities */}
            {hasEntities && (
              <div className="mt-6">
                <SectionLabel>Extracted Entities</SectionLabel>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <EntityGroup label="Organizations" items={entities.organizations} color="border-violet-200 bg-violet-50 text-violet-700" />
                  <EntityGroup label="Monetary Values" items={entities.monetary_values} color="border-emerald-200 bg-emerald-50 text-emerald-700" />
                  <EntityGroup label="Percentages" items={entities.percentages} color="border-sky-200 bg-sky-50 text-sky-700" />
                  <EntityGroup label="Dates" items={entities.dates} color="border-amber-200 bg-amber-50 text-amber-700" />
                  <EntityGroup label="Locations" items={entities.locations} color="border-rose-200 bg-rose-50 text-rose-700" />
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ── Stats bar (multi-document runs) ──────────────────────────────────────────
function StatsBar({ stats }) {
  if (!stats) return null
  const cells = [
    { label: 'Documents', value: stats.total, color: 'text-slate-800' },
    { label: 'Analyzed', value: stats.success, color: 'text-emerald-600' },
    { label: 'Empty', value: stats.empty, color: 'text-amber-600' },
    { label: 'Errors', value: stats.error, color: 'text-red-500' },
    { label: 'Time', value: `${(stats.elapsed_seconds || 0).toFixed(1)}s`, color: 'text-blue-600' },
  ]
  return (
    <div className="grid grid-cols-2 gap-2.5 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-5">
      {cells.map((c) => (
        <div key={c.label} className="text-center">
          <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
          <p className="text-[10px] font-medium uppercase tracking-wide text-slate-400">{c.label}</p>
        </div>
      ))}
    </div>
  )
}

// ── Main results view ────────────────────────────────────────────────────────
export default function ResultsView({ results, onBack }) {
  const elapsed = results.stats?.elapsed_seconds ? `${results.stats.elapsed_seconds.toFixed(1)}s` : null
  const summaries = results.summaries || []
  const isMulti = summaries.length > 1

  return (
    <div className="mx-auto max-w-3xl animate-fadeIn space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={onBack}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-600 shadow-sm transition hover:bg-slate-50 hover:shadow">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M15 18l-6-6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Back to Files
        </button>
        <div className="ml-auto flex items-center gap-2">
          <a href={EXPORT_CSV_URL}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 hover:shadow">
            <DownloadIcon /> Download CSV
          </a>
          <a href={EXPORT_PDF_URL}
            className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm transition hover:from-blue-700 hover:to-indigo-700 hover:shadow">
            <DownloadIcon /> Download PDF
          </a>
        </div>
      </div>

      {isMulti && <StatsBar stats={results.stats} />}

      <div className="space-y-5">
        {summaries.map((item) => (
          <IntelligenceCard key={item.file_id || item.file_name} item={item} elapsed={isMulti ? null : elapsed} />
        ))}
      </div>
    </div>
  )
}

function DownloadIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 3v12m0 0-4-4m4 4 4-4M5 21h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
