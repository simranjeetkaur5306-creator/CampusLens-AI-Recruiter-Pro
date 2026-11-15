import { Link, useSearchParams } from "react-router-dom";
import { ExternalLink, FileText } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import ResumeSections from "../../components/ui/ResumeSections";
import { EmptyState, ErrorState, InlineError, Spinner } from "../../components/ui/States";
import { useAsync } from "../../hooks/useAsync";
import { getResumeDetail, getResumes } from "../../services/candidateApi";
import { formatDate } from "../../utils/format";
import { isHttpUrl } from "../../utils/resumeFormat";

export default function ResumeAnalysis() {
  const [params, setParams] = useSearchParams();
  const list = useAsync(getResumes, []);
  const parsed = (list.data ?? []).filter((r) => r.parsingStatus === "success");
  const selectedId = params.get("resume") || String((parsed.find((r) => r.isActive) ?? parsed[0])?.id ?? "");
  const detail = useAsync(() => (selectedId ? getResumeDetail(selectedId) : Promise.resolve(null)), [selectedId]);

  if (list.loading) return <Spinner label="Loading resumes…" />;
  if (list.error) return <ErrorState message={list.error} onRetry={list.reload} />;

  if (parsed.length === 0) {
    return (
      <>
        <PageHeader title="Resume Analysis" />
        <EmptyState
          icon={FileText}
          title="No parsed resume yet"
          text="Upload a PDF or DOCX resume to see the skills, education and experience we extract."
          action={<Link to="/candidate/resume-upload" className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">Upload resume</Link>}
        />
      </>
    );
  }

  const r = detail.data;
  const contact = r ? [["Name", r.contact.name], ["Email", r.contact.email], ["Phone", r.contact.phone]].filter(([, v]) => v) : [];

  return (
    <>
      <PageHeader
        title="Resume Analysis"
        subtitle={r ? `${r.fileName} · uploaded ${formatDate(r.uploadedAt)}${r.isActive ? " · active" : ""}` : undefined}
        actions={
          parsed.length > 1 && (
            <select
              value={selectedId}
              onChange={(e) => setParams({ resume: e.target.value })}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              aria-label="Choose resume"
            >
              {parsed.map((x) => (
                <option key={x.id} value={String(x.id)}>{x.fileName} ({formatDate(x.uploadedAt)})</option>
              ))}
            </select>
          )
        }
      />

      <p className="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
        This information is extracted automatically and may contain errors. Unusual layouts can reduce accuracy.
      </p>

      {detail.loading ? (
        <Spinner label="Loading analysis…" />
      ) : detail.error ? (
        <InlineError what="resume analysis" message={detail.error} />
      ) : r ? (
        <div className="space-y-5">
          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="font-semibold text-navy-900">Contact details found</h2>
            {contact.length === 0 && !isHttpUrl(r.contact.linkedin) && !isHttpUrl(r.contact.github) ? (
              <p className="mt-2 text-sm text-slate-400">Not detected</p>
            ) : (
              <>
                <ul className="mt-3 space-y-1 text-sm text-slate-700">
                  {contact.map(([label, value]) => <li key={label}><span className="text-slate-500">{label}:</span> {value}</li>)}
                </ul>
                <div className="mt-2 flex gap-4 text-sm font-semibold text-brand-700">
                  {isHttpUrl(r.contact.linkedin) && <a href={r.contact.linkedin} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:underline">LinkedIn <ExternalLink size={14} /></a>}
                  {isHttpUrl(r.contact.github) && <a href={r.contact.github} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:underline">GitHub <ExternalLink size={14} /></a>}
                </div>
              </>
            )}
          </section>
          <ResumeSections resume={r} />
        </div>
      ) : null}
    </>
  );
}