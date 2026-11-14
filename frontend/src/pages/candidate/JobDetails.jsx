import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, MapPin } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import ScoreRing from "../../components/ui/ScoreRing";
import SkillChips from "../../components/ui/SkillChips";
import { ErrorState, Spinner } from "../../components/ui/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { applyToJob, getApplications, getJob, getRecommendations } from "../../services/candidateApi";

async function load(id) {
  const [job, recs, apps] = await Promise.allSettled([getJob(id), getRecommendations(), getApplications()]);
  if (job.status === "rejected") throw job.reason;
  return {
    job: job.value,
    rec: recs.status === "fulfilled" ? recs.value.find((r) => String(r.id) === String(id)) ?? null : null,
    applied: apps.status === "fulfilled" && apps.value.some((a) => String(a.jobId) === String(id)),
  };
}

export default function JobDetails() {
  const { id } = useParams();
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(() => load(id), [id]);
  const [applying, setApplying] = useState(false);
  const [appliedNow, setAppliedNow] = useState(false);

  if (loading) return <Spinner label="Loading job…" />;
  if (error || !data) return <ErrorState message={error} onRetry={reload} />;

  const { job, rec, applied } = data;
  const isApplied = applied || appliedNow;

  const onApply = async () => {
    setApplying(true);
    try {
      await applyToJob(job.id);
      setAppliedNow(true);
      toast.success(`Applied to ${job.title}.`);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setApplying(false);
    }
  };

  return (
    <>
      <Link to="/candidate/recommendations" className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline">
        <ArrowLeft size={16} /> Back to recommendations
      </Link>

      <PageHeader
        title={job.title}
        subtitle={[job.company, job.experienceLevel].filter(Boolean).join(" · ") || undefined}
        actions={
          <button
            onClick={onApply}
            disabled={isApplied || applying}
            className="rounded-lg bg-navy-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-800 disabled:opacity-60"
          >
            {isApplied ? "Applied" : applying ? "Applying…" : "Apply now"}
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <section className="rounded-2xl border border-slate-200 bg-white p-6">
            {job.location && (
              <p className="mb-3 flex items-center gap-1 text-sm text-slate-500"><MapPin size={14} /> {job.location}</p>
            )}
            <h2 className="font-semibold text-navy-900">About the role</h2>
            <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-700">
              {job.description || "No description provided."}
            </p>
          </section>
          <section className="rounded-2xl border border-slate-200 bg-white p-6">
            <h2 className="font-semibold text-navy-900">Required skills</h2>
            <div className="mt-3"><SkillChips skills={job.requiredSkills} empty="Not specified" /></div>
          </section>
        </div>

        <aside className="space-y-6">
          <section className="rounded-2xl border border-slate-200 bg-white p-6">
            <h2 className="font-semibold text-navy-900">Your match</h2>
            {rec ? (
              <>
                <div className="mt-4 flex items-center gap-4">
                  <ScoreRing value={rec.matchScore} size={80} />
                  <p className="text-sm text-slate-600">Semantic similarity between your resume and this job.</p>
                </div>
                {rec.matchedSkills.length > 0 && (
                  <div className="mt-4">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Matched</p>
                    <SkillChips skills={rec.matchedSkills} tone="matched" />
                  </div>
                )}
                {rec.missingSkills.length > 0 && (
                  <div className="mt-4">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Missing</p>
                    <SkillChips skills={rec.missingSkills} tone="missing" />
                  </div>
                )}
              </>
            ) : (
              <p className="mt-3 text-sm text-slate-500">
                No match score yet. Upload a resume to see how well you fit this job.
              </p>
            )}
          </section>

          <section className="space-y-2 rounded-2xl border border-slate-200 bg-white p-6">
            <h2 className="mb-2 font-semibold text-navy-900">Prepare</h2>
            <Link to={`/candidate/skill-gap?job=${job.id}`} className="block rounded-lg border border-slate-300 px-3 py-2 text-center text-sm font-semibold text-navy-900 hover:bg-slate-50">
              Skill gap analysis
            </Link>
            <Link to={`/candidate/interview-prep?job=${job.id}`} className="block rounded-lg border border-slate-300 px-3 py-2 text-center text-sm font-semibold text-navy-900 hover:bg-slate-50">
              AI interview questions
            </Link>
          </section>
        </aside>
      </div>
    </>
  );
}