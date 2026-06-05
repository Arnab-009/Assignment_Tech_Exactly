export default function Spinner({ label, light = false }) {
  return (
    <div className="flex items-center gap-3">
      <svg
        className="animate-spin-slow"
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <circle
          cx="12"
          cy="12"
          r="9"
          stroke={light ? 'rgba(255,255,255,0.35)' : '#cbd5e1'}
          strokeWidth="3"
        />
        <path
          d="M21 12a9 9 0 0 0-9-9"
          stroke={light ? '#ffffff' : '#2563eb'}
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
      {label && (
        <span className={light ? 'text-sm text-white' : 'text-sm text-slate-600'}>
          {label}
        </span>
      )}
    </div>
  )
}
