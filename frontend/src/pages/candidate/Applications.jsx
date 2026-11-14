import { useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardList, Search } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import { EmptyState, ErrorState, Spinner } from "../../components/ui/States";
import { useAsync } from "../../hooks/useAsync";
import { getApplications } from "../../services/candidateApi";
import { formatDate } from "../../utils/format";
import { statusLabel, statusStyle } from "../../utils/status";

function InterviewLine({ interview }) {
  const parts = [formatDate(interview.date), interview.time, interview.mode].filter((p) => p && p !== "—");
  const isLink = /^https?:\/\//i.test(interview.location);
  return (
    <div className="mt-2 rounded-lg bg-violet-50 px-3 py-2 text-xs text-violet-800">
      <span className="font-semibold">Interview:</span> {parts.join(" · ") || "Details pending"}
      {interview.location && (
        <>
          {" · "}
          {isLink ? (
            <a href={interview.location} target="_blank" rel="noopener noreferrer" className="font-medium underline">Join link</a>
          ) : (
            interview.location
          )}
        </>
      )}
      {interview.details && <p className="mt-1 text-violet-700">{interview.details}</p>}
    </div>
  );
}

export default function Applications() {
  const { data, loading, error, reload } = useAsync(getApplications, []);
  const [status, setStatus] = useState("all");
  const [query, setQuery] = useState("");

  if (loading) return <Spinner label="Loading applications…" />;
  if (error || !data) return <ErrorState message={error} onRetry={reload} />;

  if (data.length === 0) {
    return (
      <>
        <PageHeader title="My Applications" />
        <EmptyState
          icon={ClipboardList}
          title="No applications yet"
          text="Apply to a recommended job and track its status here."
          action={<Link to="/candidate/recommendations" className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">Browse recommendations</Link>}
        />
      </>
    );
  }

  const statuses = [...new Set(data.map((a) => a.status))];
  const q = query.trim().toLowerCase();
  const rows = data
    .filter((a) => status === "all" || a.status === status)
    .filter((a) => !q || `${a.jobTitle} ${a.company}`.toLowerCase().includes(q))
    .sort((a, b) => new Date(b.appliedAt || 0) - new Date(a.appliedAt || 0));

  return (
    <>
      <PageHeader title="My Applications" subtitle={`${data.length} application${data.length === 1 ? "" : "s"}`} />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative min-w-56 flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by job or company"
            aria-label="Search applications"
            className="w-full rounded-lg border border-slate-300 bg-white py-2.5 pl-9 pr-3 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden"
          />
        </div>
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status" className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm">
          <option value="all">All statuses</option>
          {statuses.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
        </select>
      </div>

      {rows.length === 0 ? (
        <EmptyState title="No applications match your filters" />
      ) : (
        <ul className="space-y-3">
          {rows.map((a) => (
            <li key={a.id} className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  {a.jobId != null ? (
                    <Link to={`/candidate/jobs/${a.jobId}`} className="font-semibold text-navy-900 hover:text-brand-700 hover:underline">{a.jobTitle}</Link>
                  ) : (
                    <span className="font-semibold text-navy-900">{a.jobTitle}</span>
                  )}
                  <p className="text-xs text-slate-500">
                    {a.company ? `${a.company} · ` : ""}Applied {formatDate(a.appliedAt)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {a.matchScore != null && <span className="text-sm font-semibold text-brand-700">{a.matchScore}% match</span>}
                  <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusStyle(a.status)}`}>{statusLabel(a.status)}</span>
                </div>
              </div>
              {a.interview && <InterviewLine interview={a.interview} />}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}