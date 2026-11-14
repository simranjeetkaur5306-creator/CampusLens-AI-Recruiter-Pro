import { useState } from "react";
import { Link } from "react-router-dom";
import { FileText } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import SkillChips from "../../components/ui/SkillChips";
import { EmptyState, ErrorState, Spinner } from "../../components/ui/States";
import { useAsync } from "../../hooks/useAsync";
import { getResumes } from "../../services/candidateApi";
import { formatDate } from "../../utils/format";

function Section({ title, items }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="font-semibold text-navy-900">{title}</h2>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-slate-400">Not detected</p>
      ) : (
        <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-slate-700">
          {items.map((it, i) => <li key={i}>{it}</li>)}
        </ul>
      )}
    </section>
  );
}

export default function ResumeAnalysis() {
  const { data, loading, error, reload } = useAsync(getResumes, []);
  const [selectedId, setSelectedId] = useState("");

  if (loading) return <Spinner label="Loading resume analysis…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  if (!data || data.length === 0) {
    return (
      <>
        <PageHeader title="Resume Analysis" />
        <EmptyState
          icon={FileText}
          title="No resume to analyse"
          text="Upload a resume to see the skills, education and experience we extract."
          action={<Link to="/candidate/resume-upload" className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">Upload resume</Link>}
        />
      </>
    );
  }

  const resume = data.find((r) => String(r.id) === selectedId) ?? data[0];
  const contact = [resume.name, resume.email, resume.phone].filter(Boolean);

  return (
    <>
      <PageHeader
        title="Resume Analysis"
        subtitle={`${resume.fileName} · uploaded ${formatDate(resume.uploadedAt)}`}
        actions={
          data.length > 1 && (
            <select
              value={String(resume.id)}
              onChange={(e) => setSelectedId(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              aria-label="Choose resume version"
            >
              {data.map((r) => (
                <option key={r.id} value={String(r.id)}>{r.fileName} ({formatDate(r.uploadedAt)})</option>
              ))}
            </select>
          )
        }
      />

      <p className="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
        This information is extracted automatically and may contain errors. Unusual layouts can reduce accuracy.
      </p>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="font-semibold text-navy-900">Contact details</h2>
          {contact.length === 0 ? (
            <p className="mt-2 text-sm text-slate-400">Not detected</p>
          ) : (
            <ul className="mt-3 space-y-1 text-sm text-slate-700">
              {contact.map((c) => <li key={c}>{c}</li>)}
            </ul>
          )}
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="font-semibold text-navy-900">Skills ({resume.skills.length})</h2>
          <div className="mt-3"><SkillChips skills={resume.skills} /></div>
        </section>

        <Section title="Education" items={resume.education} />
        <Section title="Experience" items={resume.experience} />
        <Section title="Projects" items={resume.projects} />
        <Section title="Certifications" items={resume.certifications} />
      </div>
    </>
  );
}