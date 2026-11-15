import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FileUp } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import SkillChips from "../../components/ui/SkillChips";
import { ErrorState, Spinner } from "../../components/ui/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { activateResume, deleteResume, getResumes, uploadResume } from "../../services/candidateApi";
import { formatDate } from "../../utils/format";

const MAX_MB = 5; // same as the backend limit
const MAX_RESUMES = 5; // same as the backend limit
const ALLOWED = [".pdf", ".docx"];

function validate(file) {
  const name = file.name.toLowerCase();
  if (!ALLOWED.some((ext) => name.endsWith(ext))) return "Only PDF or DOCX files are allowed.";
  if (file.size === 0) return "The file is empty.";
  if (file.size > MAX_MB * 1024 * 1024) return `File is too large (max ${MAX_MB} MB).`;
  return "";
}

const STATUS = {
  success: ["Parsed", "bg-emerald-50 text-emerald-700"],
  failed: ["Could not be parsed", "bg-rose-50 text-rose-700"],
  pending: ["Pending", "bg-amber-50 text-amber-700"],
};

export default function ResumeUpload() {
  const navigate = useNavigate();
  const toast = useToast();
  const history = useAsync(getResumes, []);
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [busyId, setBusyId] = useState(null);

  if (history.loading) return <Spinner label="Loading your resumes…" />;
  if (history.error) return <ErrorState message={history.error} onRetry={history.reload} />;

  const resumes = history.data ?? [];
  const full = resumes.length >= MAX_RESUMES;

  const pick = (f) => {
    if (!f) return;
    const problem = validate(f);
    setError(problem);
    setFile(problem ? null : f);
  };

  const onSubmit = async () => {
    if (!file) return setError("Please choose a PDF or DOCX file first.");
    setBusy(true);
    setProgress(0);
    try {
      const { resume } = await uploadResume(file, setProgress);
      if (resume.parsingStatus === "failed") {
        // Saved, but no readable text was found. It is not made active.
        const msg = resume.parsingError || "The text of this resume could not be read.";
        setError(msg);
        toast.error("Resume saved, but it could not be parsed.");
        setFile(null);
        await history.reload();
      } else {
        toast.success("Resume uploaded and analysed.");
        navigate(`/candidate/resume-analysis?resume=${resume.id}`);
      }
    } catch (err) {
      const msg = errorMessage(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  const act = async (id, action, okMessage) => {
    setBusyId(id);
    try {
      await action();
      toast.success(okMessage);
      await history.reload();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const onDelete = (r) => {
    if (!window.confirm(`Delete "${r.fileName}"? Applications you already made keep working.`)) return;
    act(r.id, () => deleteResume(r.id), "Resume deleted.");
  };

  return (
    <>
      <PageHeader
        title="Resume Upload"
        subtitle={`PDF or DOCX, up to ${MAX_MB} MB. You can keep up to ${MAX_RESUMES} resumes; the active one is used for matching and applications.`}
      />

      <div className="max-w-2xl rounded-2xl border border-slate-200 bg-white p-6">
        <label
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files?.[0]); }}
          className={`flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragging ? "border-brand-500 bg-brand-50" : "border-slate-300 hover:bg-slate-50"
          }`}
        >
          <FileUp size={28} className="text-brand-600" />
          <span className="mt-3 text-sm font-medium text-navy-900">
            {file ? file.name : "Drag and drop your resume, or click to browse"}
          </span>
          <span className="mt-1 text-xs text-slate-500">{file ? `${(file.size / 1024).toFixed(0)} KB` : "PDF or DOCX"}</span>
          <input type="file" accept=".pdf,.docx" className="hidden" onChange={(e) => pick(e.target.files?.[0])} />
        </label>

        {full && (
          <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
            You have {MAX_RESUMES} resumes. Delete one below before uploading a new one.
          </p>
        )}
        {error && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

        {busy && (
          <div className="mt-4">
            <div className="h-2 rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-brand-600 transition-all" style={{ width: `${progress}%` }} />
            </div>
            <p className="mt-2 text-xs text-slate-500">{progress < 100 ? `Uploading… ${progress}%` : "Analysing resume…"}</p>
          </div>
        )}

        <button
          onClick={onSubmit}
          disabled={busy || !file || full}
          className="mt-5 rounded-lg bg-navy-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-800 disabled:opacity-50"
        >
          {busy ? "Please wait…" : "Upload and analyse"}
        </button>
      </div>

      <h2 className="mb-3 mt-10 font-semibold text-navy-900">Your resumes ({resumes.length}/{MAX_RESUMES})</h2>
      {resumes.length === 0 ? (
        <p className="text-sm text-slate-500">No resumes uploaded yet.</p>
      ) : (
        <ul className="max-w-2xl space-y-3">
          {resumes.map((r) => {
            const [label, tone] = STATUS[r.parsingStatus] ?? [r.parsingStatus, "bg-slate-100 text-slate-600"];
            return (
              <li key={r.id} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-navy-900">{r.fileName}</p>
                    <p className="text-xs text-slate-500">Uploaded {formatDate(r.uploadedAt)}</p>
                  </div>
                  <div className="flex gap-2">
                    {r.isActive && <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">Active</span>}
                    <span className={`rounded-full px-3 py-1 text-xs font-medium ${tone}`}>{label}</span>
                  </div>
                </div>

                {r.parsingStatus === "failed" ? (
                  <p className="mt-2 text-xs text-rose-700">{r.parsingError || "No readable text was found."}</p>
                ) : (
                  <div className="mt-3"><SkillChips skills={r.skills} limit={8} empty="No skills detected" /></div>
                )}

                <div className="mt-3 flex flex-wrap gap-2">
                  {r.parsingStatus === "success" && (
                    <Link to={`/candidate/resume-analysis?resume=${r.id}`} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-navy-900 hover:bg-slate-50">Analysis</Link>
                  )}
                  {r.parsingStatus === "success" && !r.isActive && (
                    <button
                      onClick={() => act(r.id, () => activateResume(r.id), "Resume set as active.")}
                      disabled={busyId === r.id}
                      className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-navy-900 hover:bg-slate-50 disabled:opacity-50"
                    >
                      Make active
                    </button>
                  )}
                  <button
                    onClick={() => onDelete(r)}
                    disabled={busyId === r.id}
                    className="rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                  >
                    Delete
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}