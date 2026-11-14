export function Spinner({ label = "Loading…" }) {
  return (
    <div className="flex items-center justify-center gap-3 py-20 text-slate-500">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />
      {label}
    </div>
  );
}

export function InlineError({ what, message }) {
  return (
    <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">
      Could not load {what}: {message}
    </p>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="rounded-2xl border border-rose-200 bg-rose-50 p-8 text-center">
      <p className="font-semibold text-rose-800">Something went wrong</p>
      <p className="mt-1 text-sm text-rose-700">{message || "Unable to load this page."}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-4 rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, text, action }) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
      {Icon && (
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-700">
          <Icon size={22} />
        </span>
      )}
      <h3 className="mt-4 font-semibold text-navy-900">{title}</h3>
      {text && <p className="mt-1 max-w-md text-sm text-slate-500">{text}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}