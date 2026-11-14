import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ListOrdered } from "lucide-react";
import JobSelect from "../../components/ui/JobSelect";
import PageHeader from "../../components/ui/PageHeader";
import ScoreRing from "../../components/ui/ScoreRing";
import SkillChips from "../../components/ui/SkillChips";
import StatusActions from "../../components/ui/StatusActions";
import { EmptyState, ErrorState, InlineError, Spinner } from "../../components/ui/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { getManagedJobs, getRanking, updateApplicationStatus } from "../../services/recruiterApi";
import { statusLabel, statusStyle } from "../../utils/status";

export default function Ranking() {
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const jobId = params.get("job") || "";
  const [busyId, setBusyId] = useState(null);
  const jobs = useAsync(getManagedJobs, []);
  const ranking = useAsync(() => (jobId ? getRanking(jobId) : Promise.resolve(null)), [jobId]);

  if (jobs.loading) return <Spinner label="Loading jobs…" />;
  if (jobs.error) return <ErrorState message={jobs.error} onRetry={jobs.reload} />;

  const options = (jobs.data ?? []).map((j) => ({ id: j.id, title: j.title, company: "" }));
  const result = ranking.data;

  const onChange = async (row, next) => {
    setBusyId(row.applicationId);
    try {
      await updateApplicationStatus(row.applicationId, next);
      toast.success(`${row.name}: ${statusLabel(next)}.`);
      await ranking.reload();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <>
      <PageHeader title="Candidate Ranking" subtitle="Applicants ordered by semantic similarity between their resume and the job." />

      <div className="mb-4 max-w-md">
        <JobSelect options={options} value={jobId} onChange={(v) => setParams(v ? { job: v } : {})} />
      </div>

      <p className="mb-6 rounded-xl border border-brand-200 bg-brand-50 p-3 text-sm text-brand-900">
        {result?.note || "AI-assisted ranking to help you prioritise your review. It is not a hiring decision; always read the resumes and decide yourself."}
      </p>

      {!jobId ? (
        <EmptyState icon={ListOrdered} title="Choose a job" text="Select a job to see its ranked applicants." />
      ) : ranking.loading ? (
        <Spinner label="Ranking candidates…" />
      ) : ranking.error ? (
        <InlineError what="ranking" message={ranking.error} />
      ) : !result || result.rows.length === 0 ? (
        <EmptyState title="No applicants yet" text="Nobody has applied to this job yet." />
      ) : (
        <>
          <p className="mb-4 text-sm text-slate-500">
            {result.scored} of {result.total} applicant{result.total === 1 ? "" : "s"} scored. Unscored applicants are listed last.
          </p>
          <ol className="space-y-3">
            {result.rows.map((c) => (
              <li key={c.key} className="rounded-2xl border border-slate-200 bg-white p-5">
                <div className="flex items-center gap-4">
                  <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold ${c.rank ? "bg-navy-900 text-white" : "bg-slate-200 text-slate-500"}`}>
                    {c.rank ?? "–"}
                  </span>
                  <div className="min-w-0 flex-1">
                    <Link to={`/recruiter/applicants/${c.applicationId}`} className="block truncate font-semibold text-navy-900 hover:text-brand-700 hover:underline">{c.name}</Link>
                    <p className="truncate text-xs text-slate-500">{[c.email, c.university].filter(Boolean).join(" · ")}</p>
                  </div>
                  <span className={`hidden rounded-full px-3 py-1 text-xs font-medium sm:inline ${statusStyle(c.status)}`}>{statusLabel(c.status)}</span>
                  {c.scored ? <ScoreRing value={c.score} size={60} /> : <span className="text-xs text-slate-400">Not scored</span>}
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div>
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Matching skills</p>
                    <SkillChips skills={c.matched} tone="matched" empty="None" />
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Missing skills</p>
                    <SkillChips skills={c.missing} tone="missing" empty="None" />
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <StatusActions status={c.status} busy={busyId === c.applicationId} onChange={(next) => onChange(c, next)} compact />
                  <Link to={`/recruiter/applicants/${c.applicationId}`} className="text-sm font-semibold text-brand-700 hover:underline">View details</Link>
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
    </>
  );
}