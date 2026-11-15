import { useState } from "react";
import { Link } from "react-router-dom";
import { Search, Sparkles } from "lucide-react";
import JobCard from "../../components/ui/JobCard";
import PageHeader from "../../components/ui/PageHeader";
import { EmptyState, ErrorState, Spinner } from "../../components/ui/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { applyToJob, getRecommendations } from "../../services/candidateApi";

export default function Recommendations() {
  const toast = useToast();
  const [includeApplied, setIncludeApplied] = useState(false);
  const { data, loading, error, reload } = useAsync(() => getRecommendations({ includeApplied }), [includeApplied]);
  const [query, setQuery] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [sort, setSort] = useState("match");
  const [applyingId, setApplyingId] = useState(null);
  const [justApplied, setJustApplied] = useState(() => new Set());

  if (loading) return <Spinner label="Finding your best matches…" />;
  if (error || !data) {
    return (
      <>
        <PageHeader title="Job Recommendations" />
        <ErrorState message={error} onRetry={reload} />
        <p className="mt-4 text-sm text-slate-500">
          Recommendations need an active, parsed resume. <Link to="/candidate/resume-upload" className="font-semibold text-brand-700 hover:underline">Manage resumes</Link>
        </p>
      </>
    );
  }

  const isApplied = (job) => job.alreadyApplied || justApplied.has(String(job.id));

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
  const jobs = data.items
    .filter((j) => (j.matchPercent ?? 0) >= minScore)
    .filter((j) => !q || `${j.title} ${j.company} ${j.location} ${j.requiredSkills.join(" ")}`.toLowerCase().includes(q))
    .sort((a, b) => (sort === "title" ? a.title.localeCompare(b.title) : (b.matchPercent ?? -1) - (a.matchPercent ?? -1)));

  return (
    <>
      <PageHeader
        title="Job Recommendations"
        subtitle={data.resumeName ? `Ranked by semantic similarity with your active resume (${data.resumeName}).` : "Ranked by semantic similarity with your active resume."}
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative min-w-56 flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search title, company, location or skill"
            aria-label="Search jobs"
            className="w-full rounded-lg border border-slate-300 bg-white py-2.5 pl-9 pr-3 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden"
          />
        </div>
        <select value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} aria-label="Minimum match" className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm">
          <option value={0}>Any match</option>
          <option value={30}>30%+ match</option>
          <option value={50}>50%+ match</option>
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort" className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm">
          <option value="match">Best match first</option>
          <option value="title">Title A–Z</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={includeApplied} onChange={(e) => setIncludeApplied(e.target.checked)} />
          Include jobs I applied to
        </label>
      </div>

      <p className="mb-5 text-xs text-slate-500">
        The match score is the raw similarity between your resume and the job text. It is not a prediction of hiring success; even good matches rarely reach 90%.
      </p>

      {data.items.length === 0 ? (
        <EmptyState
          icon={Sparkles}
          title="No recommendations right now"
          text="There are no open jobs you have not applied to. New matches appear when recruiters publish jobs."
        />
      ) : jobs.length === 0 ? (
        <EmptyState title="No jobs match your filters" text="Try clearing the search or lowering the minimum match." />
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} applied={isApplied(job)} applying={applyingId === job.id} onApply={onApply} />
          ))}
        </div>
      )}
    </>
  );
}