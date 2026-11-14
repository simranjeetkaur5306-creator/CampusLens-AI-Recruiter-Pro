import { useState } from "react";
import { Link } from "react-router-dom";
import { Search, Users } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import SkillChips from "../../components/ui/SkillChips";
import StatusActions from "../../components/ui/StatusActions";
import { EmptyState, ErrorState, Spinner } from "../../components/ui/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { getApplicants, updateApplicationStatus } from "../../services/recruiterApi";
import { formatDate } from "../../utils/format";
import { statusLabel, statusStyle } from "../../utils/status";

export default function Applicants() {
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(getApplicants, []);
  const [status, setStatus] = useState("all");
  const [jobId, setJobId] = useState("all");
  const [query, setQuery] = useState("");
  const [busyId, setBusyId] = useState(null);

  if (loading) return <Spinner label="Loading applicants…" />;
  if (error || !data) return <ErrorState message={error} onRetry={reload} />;

  if (data.length === 0) {
    return (
      <>
        <PageHeader title="Applicants" />
        <EmptyState icon={Users} title="No applicants yet" text="Applications to your published jobs will appear here." />
      </>
    );
  }

  const onChange = async (app, next) => {
    setBusyId(app.id);
    try {
      await updateApplicationStatus(app.id, next);
      toast.success(`${app.name}: ${statusLabel(next)}.`);
      await reload();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const statuses = [...new Set(data.map((a) => a.status))];
  const jobs = [...new Map(data.map((a) => [String(a.jobId), a.jobTitle])).entries()];
  const q = query.trim().toLowerCase();
  const rows = data
    .filter((a) => status === "all" || a.status === status)
    .filter((a) => jobId === "all" || String(a.jobId) === jobId)
    .filter((a) => !q || `${a.name} ${a.email} ${a.skills.join(" ")}`.toLowerCase().includes(q));

  return (
    <>
      <PageHeader title="Applicants" subtitle={`${data.length} application${data.length === 1 ? "" : "s"}, newest first`} />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative min-w-56 flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search name, email or skill"
            aria-label="Search applicants"
            className="w-full rounded-lg border border-slate-300 bg-white py-2.5 pl-9 pr-3 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden"
          />
        </div>
        <select value={jobId} onChange={(e) => setJobId(e.target.value)} aria-label="Filter by job" className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm">
          <option value="all">All jobs</option>
          {jobs.map(([id, title]) => <option key={id} value={id}>{title}</option>)}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status" className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm">
          <option value="all">All statuses</option>
          {statuses.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
        </select>
      </div>

      {rows.length === 0 ? (
        <EmptyState title="No applicants match your filters" />
      ) : (
        <ul className="space-y-3">
          {rows.map((a) => (
            <li key={a.id} className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <Link to={`/recruiter/applicants/${a.id}`} className="font-semibold text-navy-900 hover:text-brand-700 hover:underline">{a.name}</Link>
                  <p className="text-xs text-slate-500">{[a.email, a.jobTitle, `Applied ${formatDate(a.appliedAt)}`].filter(Boolean).join(" · ")}</p>
                  {a.headline && <p className="mt-1 text-sm text-slate-600">{a.headline}</p>}
                </div>
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusStyle(a.status)}`}>{statusLabel(a.status)}</span>
              </div>
              <div className="mt-3"><SkillChips skills={a.skills} tone="brand" limit={8} empty="No skills extracted" /></div>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <StatusActions status={a.status} busy={busyId === a.id} onChange={(next) => onChange(a, next)} compact />
                <div className="flex gap-4 text-sm font-semibold text-brand-700">
                  <Link to={`/recruiter/applicants/${a.id}`} className="hover:underline">View details</Link>
                  <Link to={`/recruiter/ranking?job=${a.jobId}`} className="hover:underline">Job ranking</Link>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}