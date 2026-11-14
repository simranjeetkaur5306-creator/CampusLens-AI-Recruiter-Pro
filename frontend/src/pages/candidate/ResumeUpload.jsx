import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileUp } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import SkillChips from "../../components/ui/SkillChips";
import { InlineError, Spinner } from "../../components/ui/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { getResumes, uploadResume } from "../../services/candidateApi";
import { formatDate } from "../../utils/format";

const MAX_MB = 5; // keep in sync with your backend limit
const ALLOWED = [".pdf", ".docx"];

function validate(file) {
  const name = file.name.toLowerCase();
  if (!ALLOWED.some((ext) => name.endsWith(ext))) return "Only PDF or DOCX files are allowed.";
  if (file.size === 0) return "The file is empty.";
  if (file.size > MAX_MB * 1024 * 1024) return `File is too large (max ${MAX_MB} MB).`;
  return "";
}

export default function ResumeUpload() {
  const navigate = useNavigate();
  const toast = useToast();
  const history = useAsync(getResumes, []);
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);

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
      await uploadResume(file, setProgress);
      toast.success("Resume uploaded and analysed.");
      navigate("/candidate/resume-analysis");
    } catch (err) {
      const msg = errorMessage(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Resume Upload" subtitle={`PDF or DOCX, up to ${MAX_MB} MB. Text is extracted and analysed on our server.`} />

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
          <span className="mt-1 text-xs text-slate-500">
            {file ? `${(file.size / 1024).toFixed(0)} KB` : "PDF or DOCX"}
          </span>
          <input
            type="file"
            accept=".pdf,.docx"
            className="hidden"
            onChange={(e) => pick(e.target.files?.[0])}
          />
        </label>

        {error && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

        {busy && (
          <div className="mt-4">
            <div className="h-2 rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-brand-600 transition-all" style={{ width: `${progress}%` }} />
            </div>
            <p className="mt-2 text-xs text-slate-500">
              {progress < 100 ? `Uploading… ${progress}%` : "Analysing resume…"}
            </p>
          </div>
        )}

        <button
          onClick={onSubmit}
          disabled={busy || !file}
          className="mt-5 rounded-lg bg-navy-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-800 disabled:opacity-50"
        >
          {busy ? "Please wait…" : "Upload and analyse"}
        </button>
      </div>

      <h2 className="mb-3 mt-10 font-semibold text-navy-900">Previous uploads</h2>
      {history.loading ? (
        <Spinner label="Loading uploads…" />
      ) : history.error ? (
        <InlineError what="previous uploads" message={history.error} />
      ) : history.data.length === 0 ? (
        <p className="text-sm text-slate-500">No resumes uploaded yet.</p>
      ) : (
        <ul className="max-w-2xl space-y-3">
          {history.data.map((r) => (
            <li key={r.id} className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-sm font-medium text-navy-900">{r.fileName}</p>
              <p className="text-xs text-slate-500">Uploaded {formatDate(r.uploadedAt)}</p>
              <div className="mt-3"><SkillChips skills={r.skills} limit={8} /></div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}