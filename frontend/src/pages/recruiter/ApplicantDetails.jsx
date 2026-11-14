import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ExternalLink, FileText } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import QuestionSections from "../../components/ui/QuestionSections";
import ResumeSections from "../../components/ui/ResumeSections";
import StatusActions from "../../components/ui/StatusActions";
import { ErrorState, Spinner } from "../../components/ui/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import {
  fetchResumeFile,
  generateApplicantQuestions,
  getApplicantDetail,
  updateApplicationStatus,
} from "../../services/recruiterApi";
import { formatDate } from "../../utils/format";
import { isHttpUrl } from "../../utils/resumeFormat";
import { statusLabel, statusStyle } from "../../utils/status";

function Row({ label, value }) {
  if (!value) return null;
  return (
    <div className="flex justify-between gap-4 py-1.5 text-sm">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium text-navy-900">{value}</dd>
    </div>
  );
}

export default function ApplicantDetails() {
  const { id } = useParams();
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(() => getApplicantDetail(id), [id]);
  const [busy, setBusy] = useState(false);
  const [fileBusy, setFileBusy] = useState(false);
  const [qBusy, setQBusy] = useState(false);
  const [questions, setQuestions] = useState(null);

  if (loading) return <Spinner label="Loading applicant…" />;
  if (error || !data) return <ErrorState message={error} onRetry={reload} />;

  const a = data;
  const resume = a.resume;

  const onStatus = async (next) => {
    setBusy(true);
    try {
      await updateApplicationStatus(a.id, next);
      toast.success(`${a.name}: ${statusLabel(next)}.`);
      await reload();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const onViewFile = async () => {
    setFileBusy(true);
    try {
      const { blob, type } = await fetchResumeFile(a.id);
      const url = URL.createObjectURL(blob);
      if (type.includes("pdf")) {
        if (!window.open(url, "_blank", "noopener")) toast.error("Your browser blocked the new tab. Allow pop-ups and try again.");
      } else {
        const link = document.createElement("a");
        link.href = url;
        link.download = resume?.fileName || "resume";
        link.click();
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setFileBusy(false);
    }
  };

  const onQuestions = async () => {
    setQBusy(true);
    try {
      setQuestions(await generateApplicantQuestions(a.id));
      toast.success("Interview questions generated.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setQBusy(false);
    }
  };

  return (
    <>
      <Link to="/recruiter/applicants" className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline">
        <ArrowLeft size={16} /> Back to applicants
      </Link>

      <PageHeader
        title={a.name}
        subtitle={[a.headline, `Applied to ${a.jobTitle} on ${formatDate(a.appliedAt)}`].filter(Boolean).join(" · ")}
        actions={<span className={`rounded-full px-3 py-1 text-sm font-medium ${statusStyle(a.status)}`}>{statusLabel(a.status)}</span>}
      />

      <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="mb-3 font-semibold text-navy-900">Decision</h2>
        <StatusActions status={a.status} busy={busy} onChange={onStatus} />
        <p className="mt-3 text-xs text-slate-500">Status changes are made by you. The AI ranking is only an aid.</p>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="font-semibold text-navy-900">Candidate</h2>
          <dl className="mt-3 divide-y divide-slate-100">
            <Row label="Email" value={a.email} />
            <Row label="Location" value={a.location} />
            <Row label="University" value={a.university} />
            <Row label="Degree" value={a.degree} />
            <Row label="Graduation year" value={a.graduationYear ? String(a.graduationYear) : ""} />
          </dl>
          <div className="mt-3 flex gap-4 text-sm font-semibold text-brand-700">
            {isHttpUrl(a.linkedinUrl) && (
              <a href={a.linkedinUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:underline">LinkedIn <ExternalLink size={14} /></a>
            )}
            {isHttpUrl(a.githubUrl) && (
              <a href={a.githubUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:underline">GitHub <ExternalLink size={14} /></a>
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold text-navy-900">Resume</h2>
              <p className="text-xs text-slate-500">
                {resume ? `${resume.fileName} · uploaded ${formatDate(resume.uploadedAt)}` : "The candidate deleted this resume after applying."}
              </p>
            </div>
            {resume?.hasFile && (
              <button
                onClick={onViewFile}
                disabled={fileBusy}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-navy-900 hover:bg-slate-50 disabled:opacity-50"
              >
                <FileText size={16} /> {fileBusy ? "Opening…" : "View resume file"}
              </button>
            )}
          </div>
          <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">
            The sections below are extracted automatically and may contain errors. Check the original file for anything important.
          </p>
        </section>
      </div>

      {resume && <div className="mt-6"><ResumeSections resume={resume} /></div>}

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold text-navy-900">Interview questions</h2>
            <p className="text-xs text-slate-500">AI-generated from the job and this candidate&apos;s skills, experience and projects. Contact details are never sent to the AI.</p>
          </div>
          <button
            onClick={onQuestions}
            disabled={qBusy}
            className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800 disabled:opacity-60"
          >
            {qBusy ? "Generating…" : questions ? "Generate again" : "Generate questions"}
          </button>
        </div>
        {qBusy && <Spinner label="Generating questions…" />}
        {!qBusy && questions && (
          <div className="mt-5">
            <QuestionSections key={questions.id ?? "set"} set={questions} />
          </div>
        )}
      </section>
    </>
  );
}