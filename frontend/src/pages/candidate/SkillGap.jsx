import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Target } from "lucide-react";
import JobSelect from "../../components/ui/JobSelect";
import PageHeader from "../../components/ui/PageHeader";
import ScoreRing from "../../components/ui/ScoreRing";
import SkillChips from "../../components/ui/SkillChips";
import SkillGapChart from "../../components/ui/SkillGapChart";
import { EmptyState, ErrorState, InlineError, Spinner } from "../../components/ui/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { getAiSummary, getJobOptions, getSkillGap } from "../../services/candidateApi";

export default function SkillGap() {
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const jobId = params.get("job") || "";
  const [ai, setAi] = useState({ jobId: "", text: "", model: "", note: "" });
  const [aiBusy, setAiBusy] = useState(false);

  const options = useAsync(getJobOptions, []);
  const result = useAsync(() => (jobId ? getSkillGap(jobId) : Promise.resolve(null)), [jobId]);

  if (options.loading) return <Spinner label="Loading jobs…" />;
  if (options.error) return <ErrorState message={options.error} onRetry={options.reload} />;

  const gap = result.data;
  const aiForJob = ai.jobId === jobId ? ai : null;

  const onAiSummary = async () => {
    setAiBusy(true);
    try {
      const res = await getAiSummary(jobId);
      if (!res.text) toast.error("The AI service returned no summary.");
      else setAi({ jobId, ...res });
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setAiBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Skill Gap Analysis" subtitle="Compare the skills on your resume with a job's requirements." />

      <div className="mb-6 max-w-md">
        <JobSelect options={options.data ?? []} value={jobId} onChange={(v) => setParams(v ? { job: v } : {})} />
      </div>

      {(options.data ?? []).length === 0 && !jobId ? (
        <EmptyState
          icon={Target}
          title="No jobs to analyse yet"
          text="Upload a resume to get job matches, or apply to a job. Then pick it here."
          action={<Link to="/candidate/resume-upload" className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">Upload resume</Link>}
        />
      ) : !jobId ? (
        <EmptyState icon={Target} title="Choose a job" text="Select a job above to see which skills you have, partly have or are missing." />
      ) : result.loading ? (
        <Spinner label="Analysing skills…" />
      ) : result.error ? (
        <InlineError what="skill gap analysis" message={result.error} />
      ) : gap && gap.total === 0 ? (
        <EmptyState title="No required skills listed" text={gap.summary || "This job does not list any required skills, so there is nothing to compare."} />
      ) : gap ? (
        <>
          <p className="mb-5 text-sm text-slate-600">
            {gap.summary} <span className="text-slate-400">· Compared with {gap.resumeName || "your resume"}{gap.resumeActive ? " (active)" : ""}</span>
          </p>

          <div className="grid gap-6 lg:grid-cols-3">
            <section className="rounded-2xl border border-slate-200 bg-white p-6">
              <h2 className="font-semibold text-navy-900">Coverage</h2>
              <div className="mt-4 flex items-center gap-4">
                <ScoreRing value={gap.coverage} size={84} />
                <p className="text-sm text-slate-600">{gap.matched.length} matched, {gap.partial.length} partial, {gap.missing.length} missing of {gap.total}</p>
              </div>
              <SkillGapChart matched={gap.matched.length} partial={gap.partial.length} missing={gap.missing.length} />
              {gap.coverageRule && <p className="mt-2 text-xs text-slate-500">Rule: {gap.coverageRule}.</p>}
            </section>

            <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 lg:col-span-2">
              <div>
                <h2 className="mb-2 text-sm font-semibold text-emerald-700">Matched ({gap.matched.length})</h2>
                <SkillChips skills={gap.matched.map((r) => r.skill)} tone="matched" empty="None" />
              </div>
              <div>
                <h2 className="mb-2 text-sm font-semibold text-amber-700">Partial ({gap.partial.length})</h2>
                {gap.partial.length === 0 ? (
                  <p className="text-sm text-slate-400">None</p>
                ) : (
                  <ul className="space-y-2">
                    {gap.partial.map((r) => (
                      <li key={r.skill} className="rounded-lg bg-amber-50 p-3 text-sm">
                        <span className="font-medium text-amber-800">{r.skill}</span>
                        {r.note && <p className="mt-0.5 text-xs text-amber-700">{r.note}</p>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <h2 className="mb-2 text-sm font-semibold text-rose-700">Missing ({gap.missing.length})</h2>
                <SkillChips skills={gap.missing.map((r) => r.skill)} tone="missing" empty="None. Every required skill is on your resume." />
              </div>
            </section>
          </div>

          {gap.plan.length > 0 && (
            <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6">
              <h2 className="font-semibold text-navy-900">What to learn next</h2>
              <p className="mt-1 text-xs text-slate-500">Ordered so that prerequisites come first.</p>
              <ol className="mt-4 space-y-4">
                {gap.plan.map((p) => (
                  <li key={p.skill} className="rounded-xl border border-slate-200 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-navy-900 text-xs font-bold text-white">{p.priority}</span>
                      <span className="font-semibold text-navy-900">{p.skill}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${p.status === "missing" ? "bg-rose-50 text-rose-700" : "bg-amber-50 text-amber-700"}`}>{p.status}</span>
                      {p.source === "generic" && <span className="text-xs text-slate-400">general guidance</span>}
                    </div>
                    {p.learnAfter.length > 0 && <p className="mt-2 text-xs text-slate-500">Learn first: {p.learnAfter.join(", ")}</p>}
                    {p.topics.length > 0 && (
                      <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-slate-700">
                        {p.topics.map((t, i) => <li key={i}>{t}</li>)}
                      </ul>
                    )}
                    {p.projectIdea && <p className="mt-2 text-sm text-slate-700"><span className="font-medium text-navy-900">Project idea:</span> {p.projectIdea}</p>}
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section className="mt-6 rounded-2xl border border-brand-200 bg-brand-50 p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-semibold text-navy-900">AI summary</h2>
              <button
                onClick={onAiSummary}
                disabled={aiBusy}
                className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800 disabled:opacity-60"
              >
                {aiBusy ? "Generating…" : aiForJob ? "Regenerate" : "Generate AI summary"}
              </button>
            </div>
            {aiForJob ? (
              <>
                <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-slate-700">{aiForJob.text}</p>
                <p className="mt-2 text-xs text-slate-500">{aiForJob.note || "Written by AI from the comparison above. It cannot add skills."}{aiForJob.model ? ` (${aiForJob.model})` : ""}</p>
              </>
            ) : (
              <p className="mt-3 text-sm text-slate-500">A short plain-language summary of the comparison above. The skill lists themselves are rule-based, not written by AI. AI features have an hourly limit.</p>
            )}
          </section>

          {gap.disclaimer && <p className="mt-4 text-xs text-slate-500">{gap.disclaimer}</p>}

          <div className="mt-6">
            <Link to={`/candidate/interview-prep?job=${jobId}`} className="text-sm font-semibold text-brand-700 hover:underline">
              Prepare for this job with AI interview questions →
            </Link>
          </div>
        </>
      ) : null}
    </>
  );
}