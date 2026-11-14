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
  const [ai, setAi] = useState({ jobId: "", text: "" });
  const [aiBusy, setAiBusy] = useState(false);

  const options = useAsync(getJobOptions, []);
  const result = useAsync(() => (jobId ? getSkillGap(jobId) : Promise.resolve(null)), [jobId]);

  if (options.loading) return <Spinner label="Loading jobs…" />;
  if (options.error) return <ErrorState message={options.error} onRetry={options.reload} />;

  const gap = result.data;
  const total = gap ? gap.matched.length + gap.partial.length + gap.missing.length : 0;
  const pct = total ? Math.round((gap.matched.length / total) * 100) : null;
  const aiText = ai.jobId === jobId ? ai.text : "";

  const onAiSummary = async () => {
    setAiBusy(true);
    try {
      const text = await getAiSummary(jobId);
      if (!text) toast.error("The AI service returned no summary.");
      else setAi({ jobId, text });
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setAiBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Skill Gap Analysis" subtitle="Compare your resume skills with a job's requirements." />

      <div className="mb-6 max-w-md">
        <JobSelect options={options.data ?? []} value={jobId} onChange={(v) => setParams(v ? { job: v } : {})} />
      </div>

      {!jobId ? (
        <EmptyState icon={Target} title="Choose a job" text="Select a job above to see which skills you have, partly have or are missing." />
      ) : result.loading ? (
        <Spinner label="Analysing skills…" />
      ) : result.error ? (
        <InlineError what="skill gap analysis" message={result.error} />
      ) : gap && total === 0 ? (
        <EmptyState title="No skills to compare" text="This job lists no required skills, or no skills were found on your resume." />
      ) : gap ? (
        <>
          <div className="grid gap-6 lg:grid-cols-3">
            <section className="rounded-2xl border border-slate-200 bg-white p-6">
              <h2 className="font-semibold text-navy-900">Coverage</h2>
              <div className="mt-4 flex items-center gap-4">
                <ScoreRing value={pct} size={84} />
                <p className="text-sm text-slate-600">{gap.matched.length} of {total} skills fully matched</p>
              </div>
              <SkillGapChart matched={gap.matched.length} partial={gap.partial.length} missing={gap.missing.length} />
            </section>

            <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 lg:col-span-2">
              <div>
                <h2 className="mb-2 text-sm font-semibold text-emerald-700">Matched ({gap.matched.length})</h2>
                <SkillChips skills={gap.matched} tone="matched" empty="None" />
              </div>
              <div>
                <h2 className="mb-2 text-sm font-semibold text-amber-700">Partial ({gap.partial.length})</h2>
                <SkillChips skills={gap.partial} tone="partial" empty="None" />
              </div>
              <div>
                <h2 className="mb-2 text-sm font-semibold text-rose-700">Missing ({gap.missing.length})</h2>
                <SkillChips skills={gap.missing} tone="missing" empty="None. You cover every required skill." />
              </div>
            </section>
          </div>

          {gap.recommendations.length > 0 && (
            <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6">
              <h2 className="font-semibold text-navy-900">What to learn next</h2>
              <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-slate-700">
                {gap.recommendations.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
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
                {aiBusy ? "Generating…" : aiText ? "Regenerate" : "Generate AI summary"}
              </button>
            </div>
            {gap.summary && !aiText && (
              <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-slate-700">{gap.summary}</p>
            )}
            {aiText && (
              <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-slate-700">{aiText}</p>
            )}
            {!gap.summary && !aiText && (
              <p className="mt-3 text-sm text-slate-500">
                A short natural-language summary based on the skill comparison above. Skills are never invented; the comparison stays rule-based.
              </p>
            )}
          </section>

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