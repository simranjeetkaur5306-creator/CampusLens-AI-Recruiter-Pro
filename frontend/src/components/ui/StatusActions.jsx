// Recruiter decision buttons. The recruiter chooses; nothing here is automatic.
export default function StatusActions({ status, busy, onChange, compact = false }) {
  const base = compact ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm";
  const btn = (label, value, tone) => (
    <button
      key={value}
      type="button"
      disabled={busy}
      onClick={() => onChange(value)}
      className={`rounded-lg font-semibold transition disabled:opacity-50 ${base} ${tone}`}
    >
      {label}
    </button>
  );

  if (status === "interview_scheduled") {
    return <span className="text-xs text-slate-500">Interview scheduled. Status changes are limited until scheduling is available.</span>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {status !== "shortlisted" && btn("Shortlist", "shortlisted", "bg-emerald-600 text-white hover:bg-emerald-700")}
      {status !== "rejected" && btn("Reject", "rejected", "border border-rose-200 text-rose-700 hover:bg-rose-50")}
      {status !== "applied" && btn("Reset to applied", "applied", "border border-slate-300 text-navy-900 hover:bg-slate-50")}
    </div>
  );
}