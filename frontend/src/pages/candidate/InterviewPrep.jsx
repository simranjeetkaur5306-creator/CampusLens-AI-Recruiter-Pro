import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { MessageSquare } from "lucide-react";
import JobSelect from "../../components/ui/JobSelect";
import PageHeader from "../../components/ui/PageHeader";
import QuestionSections from "../../components/ui/QuestionSections";
import { EmptyState, ErrorState, InlineError, Spinner } from "../../components/ui/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { getJobOptions } from "../../services/candidateApi";
import { deleteQuestionSet, generateQuestions, getQuestionHistory } from "../../services/interviewApi";
import { formatDate } from "../../utils/format";

export default function InterviewPrep() {
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const jobId = params.get("job") || "";
  const [result, setResult] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const options = useAsync(getJobOptions, []);
  const history = useAsync(
    () => (jobId ? getQuestionHistory(jobId) : Promise.resolve([])),
    [jobId, refreshKey]
  );

  if (options.loading) return <Spinner label="Loading jobs…" />;
  if (options.error) return <ErrorState message={options.error} onRetry={options.reload} />;

  const onJobChange = (v) => {
    setResult(null);
    setParams(v ? { job: v } : {});
  };

  const onGenerate = async () => {
    setGenerating(true);
    try {
      const set = await generateQuestions(jobId);
      setResult(set);
      setRefreshKey((k) => k + 1);
      toast.success("Interview questions generated.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setGenerating(false);
    }
  };

  const onDelete = async (set) => {
    if (!window.confirm("Delete this saved set of questions?")) return;
    try {
      await deleteQuestionSet(set.id);
      if (result?.id === set.id) setResult(null);
      setRefreshKey((k) => k + 1);
      toast.success("Deleted.");
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  const noJobs = (options.data ?? []).length === 0 && !jobId;

  return (
    <>
      <PageHeader title="AI Interview Preparation" subtitle="Practice questions based on the job and the skills, experience and projects on your active resume." />

      {noJobs ? (
        <EmptyState
          icon={MessageSquare}
          title="No jobs to prepare for yet"
          text="Upload a resume to get job matches, or apply to a job. Then pick it here."
          action={<Link to="/candidate/resume-upload" className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">Upload resume</Link>}
        />
      ) : (
        <>
          <div className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-[1fr_auto] sm:items-end">
            <JobSelect options={options.data ?? []} value={jobId} onChange={onJobChange} />
            <button
              onClick={onGenerate}
              disabled={!jobId || generating}
              className="rounded-lg bg-navy-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-800 disabled:opacity-50"
            >
              {generating ? "Generating…" : "Generate questions"}
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Technical, conceptual, project-based and HR questions are generated together. Your contact details and raw resume text are never sent to the AI. AI features have an hourly limit.
          </p>

          {generating && <Spinner label="Generating questions…" />}

          {!generating && !result && (
            <div className="mt-6">
              <EmptyState
                icon={MessageSquare}
                title={jobId ? "Ready when you are" : "Choose a job"}
                text={jobId ? "Press Generate to create a practice set, or open a saved one below." : "Select a job to prepare for."}
              />
            </div>
          )}

          {!generating && result && (
            <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
              <p className="mb-4 text-xs text-slate-500">
                {result.jobTitle ? `${result.jobTitle} · ` : ""}{result.count} questions · generated {formatDate(result.createdAt)}
                {result.model ? ` by ${result.model}` : ""}
              </p>
              <QuestionSections key={result.id ?? "set"} set={result} />
            </section>
          )}

          {jobId && (
            <section className="mt-8">
              <h2 className="mb-3 font-semibold text-navy-900">Saved sets for this job</h2>
              {history.loading ? (
                <Spinner label="Loading saved sets…" />
              ) : history.error ? (
                <InlineError what="saved sets" message={history.error} />
              ) : history.data.length === 0 ? (
                <p className="text-sm text-slate-500">Nothing generated for this job yet.</p>
              ) : (
                <ul className="space-y-2">
                  {history.data.map((h) => (
                    <li key={h.id} className="flex items-center gap-2">
                      <button
                        onClick={() => setResult(h)}
                        className="flex flex-1 items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-sm hover:bg-slate-50"
                      >
                        <span>{formatDate(h.createdAt)}</span>
                        <span className="text-xs text-slate-500">{h.count} questions</span>
                      </button>
                      <button onClick={() => onDelete(h)} className="rounded-lg border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50">Delete</button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </>
      )}
    </>
  );
}