const VARIANTS = {
  error: 'border-red-200 bg-red-50 text-red-800',
  info: 'border-blue-200 bg-blue-50 text-blue-800',
  success: 'border-green-200 bg-green-50 text-green-800',
}

export default function Alert({ variant = 'info', onClose, children }) {
  return (
    <div
      className={`mb-6 flex items-start justify-between gap-3 rounded-lg border px-4 py-3 text-sm ${VARIANTS[variant]}`}
      role="alert"
    >
      <span>{children}</span>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 text-current opacity-60 transition hover:opacity-100"
          aria-label="Dismiss"
        >
          ✕
        </button>
      )}
    </div>
  )
}
