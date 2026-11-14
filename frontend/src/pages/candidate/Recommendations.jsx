import { useState } from "react";
import { Link } from "react-router-dom";
import { Search, Sparkles } from "lucide-react";
import JobCard from "../../components/ui/JobCard";
import PageHeader from "../../components/ui/PageHeader";
import { EmptyState, ErrorState, Spinner } from "../../components/ui/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { applyToJob, getApplications, getRecommendations } from "../../services/candidateApi";

async function load() {
  const [recs, apps] = await Promise.allSettled([getRecommendations(), getApplications()]);
  if (recs.status === "rejected") throw recs.reason;
  return {
    jobs: recs.value,
    applied: apps.status === "fulfilled" ? new Set(apps.value.map((a) => String(a.jobId))) : new Set(),
  };
}

export default function Recommendations() {
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(load, []);
  const [query, setQuery] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [sort, setSort] = useState("match");
  const [applyingId, setApplyingId] = useState(null);
  const [justApplied, setJustApplied] = useState(() => new Set());

  if (loading) return <Spinner label="Finding your best matches…" />;
  if (error || !data) return <ErrorState message={error} onRetry={reload} />;

  const isApplied = (id) => data.applied.has(String(id)) || justApplied.has(String(id));

  const onApply = async (job) => {
    setApplyingId(job.id);
    try {
      await applyToJob(job.id);
      setJustApplied((prev) => new Set(prev).add(String(job.id)));
      toast.success(`Applied to ${job.title}.`);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setApplyingId(null);
    }
  };

  const q = query.trim().toLowerCase();
  const jobs = data.jobs
    .filter((j) => (j.matchScore ?? 0) >= minScore)
    .filter((j) => !q || `${j.title} ${j.company} ${j.requiredSkills.join(" ")}`.toLowerCase().includes(q))
    .sort((a, b) =>
      sort === "title" ? a.title.localeCompare(b.title) : (b.matchScore ?? -1) - (a.matchScore ?? -1)
    );

  return (
    <>
      <PageHeader title="Job Recommendations" subtitle="Jobs ranked by semantic similarity with your resume." />

      {data.jobs.length === 0 ? (
        <EmptyState
          icon={Sparkles}
          title="No recommendations yet"
          text="Upload a resume and make sure published jobs exist. Matches appear automatically."
          action={<Link to="/candidate/resume-upload" className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">Upload resume</Link>}
        />
      ) : (
        <>
          <div className="mb-5 flex flex-wrap items-center gap-3">
            <div className="relative min-w-56 flex-1">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search title, company or skill"
                aria-label="Search jobs"
                className="w-full rounded-lg border border-slate-300 bg-white py-2.5 pl-9 pr-3 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden"
              />
            </div>
            <select value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} aria-label="Minimum match" className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm">
              <option value={0}>Any match</option>
              <option value={50}>50%+ match</option>
              <option value={70}>70%+ match</option>
            </select>
            <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort" className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm">
              <option value="match">Best match first</option>
              <option value="title">Title A–Z</option>
            </select>
          </div>

          {jobs.length === 0 ? (
            <EmptyState title="No jobs match your filters" text="Try clearing the search or lowering the minimum match." />
          ) : (
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  applied={isApplied(job.id)}
                  applying={applyingId === job.id}
                  onApply={onApply}
                />
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}