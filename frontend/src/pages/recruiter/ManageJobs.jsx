import { useState } from "react";
import { Link } from "react-router-dom";
import { Briefcase, Search } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import SkillChips from "../../components/ui/SkillChips";
import { EmptyState, ErrorState, Spinner } from "../../components/ui/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { JOB_TYPES, deleteJob, getManagedJobs, setJobActive } from "../../services/recruiterApi";
import { formatDate } from "../../utils/format";

const typeLabel = (v) => JOB_TYPES.find(([value]) => value === v)?.[1] ?? v;

export default function ManageJobs() {
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(getManagedJobs, []);
  const [query, setQuery] = useState("");
  const [busyId, setBusyId] = useState(null);

  if (loading) return <Spinner label="Loading jobs…" />;
  if (error || !data) return <ErrorState message={error} onRetry={reload} />;

  const run = async (job, action, okMessage) => {
    setBusyId(job.id);
    try {
      await action();
      toast.success(okMessage);
      await reload();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const onToggle = (job) =>
    run(job, () => setJobActive(job.id, !job.isActive), job.isActive ? "Job unpublished." : "Job published.");

  const onDelete = (job) => {
    if (!window.confirm(`Delete "${job.title}"? This cannot be undone. (Jobs with applications cannot be deleted; unpublish them instead.)`)) return;
    run(job, () => deleteJob(job.id), "Job deleted.");
  };

  const q = query.trim().toLowerCase();
  const jobs = data.filter((j) => !q || `${j.title} ${j.location} ${j.company}`.toLowerCase().includes(q));

  return (
    <>
      <PageHeader
        title="Manage Jobs"
        subtitle={`${data.length} job${data.length === 1 ? "" : "s"}`}
        actions={
          <Link to="/recruiter/jobs/new" className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">
            Create job
          </Link>
        }
      />

      {data.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="No jobs yet"
          text="Create a job and publish it so candidates can find and apply."
          action={<Link to="/recruiter/jobs/new" className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">Create job</Link>}
        />
      ) : (
        <>
          <div className="relative mb-5 max-w-md">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by title, company or location"
              aria-label="Search jobs"
              className="w-full rounded-lg border border-slate-300 bg-white py-2.5 pl-9 pr-3 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden"
            />
          </div>

          {jobs.length === 0 ? (
            <EmptyState title="No jobs match your search" />
          ) : (
            <ul className="space-y-3">
              {jobs.map((job) => (
                <li key={job.id} className="rounded-2xl border border-slate-200 bg-white p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="font-semibold text-navy-900">{job.title}</h3>
                      <p className="text-xs text-slate-500">
                        {[job.company, job.location, typeLabel(job.jobType), `Created ${formatDate(job.createdAt)}`].filter(Boolean).join(" · ")}
                      </p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-medium ${job.isActive ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                      {job.isActive ? "Published" : "Unpublished"}
                    </span>
                  </div>

                  <div className="mt-3"><SkillChips skills={job.requiredSkills} tone="brand" limit={8} empty="No required skills" /></div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      onClick={() => onToggle(job)}
                      disabled={busyId === job.id}
                      className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-navy-900 hover:bg-slate-50 disabled:opacity-50"
                    >
                      {job.isActive ? "Unpublish" : "Publish"}
                    </button>
                    <Link to={`/recruiter/jobs/${job.id}/edit`} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-navy-900 hover:bg-slate-50">Edit</Link>
                    <Link to={`/recruiter/ranking?job=${job.id}`} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-navy-900 hover:bg-slate-50">View ranking</Link>
                    <button
                      onClick={() => onDelete(job)}
                      disabled={busyId === job.id}
                      className="rounded-lg border border-rose-200 px-3 py-1.5 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </>
  );
}