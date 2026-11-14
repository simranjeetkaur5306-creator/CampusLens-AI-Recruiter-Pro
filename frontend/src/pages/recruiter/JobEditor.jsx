import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import PageHeader from "../../components/ui/PageHeader";
import { ErrorState, Spinner } from "../../components/ui/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { JOB_TYPES, createJob, getManagedJob, parseSkills, updateJob } from "../../services/recruiterApi";

const input =
  "w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden";

function Field({ id, label, hint, children }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

function JobForm({ job }) {
  const navigate = useNavigate();
  const toast = useToast();
  const editing = Boolean(job);
  const [v, setV] = useState({
    title: job?.title ?? "",
    company: job?.company ?? "",
    location: job?.location ?? "",
    jobType: job?.jobType ?? "full_time",
    description: job?.description ?? "",
    skills: job ? job.requiredSkills.join(", ") : "",
    requiredExperience: job?.requiredExperience ?? 0,
    requiredEducation: job?.requiredEducation ?? "",
    salaryRange: job?.salaryRange ?? "",
    isActive: job ? job.isActive : true,
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setV({ ...v, [key]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (v.title.trim().length < 3) return setError("Job title must be at least 3 characters.");
    if (!v.location.trim()) return setError("Please enter a location.");
    if (v.description.trim().length < 30) return setError("Please describe the role in at least 30 characters.");
    if (parseSkills(v.skills).length === 0) return setError("Add at least one required skill (comma separated).");
    const years = Number(v.requiredExperience);
    if (!Number.isInteger(years) || years < 0 || years > 40) return setError("Experience must be a whole number from 0 to 40.");

    setBusy(true);
    try {
      if (editing) await updateJob(job.id, v);
      else await createJob(v);
      toast.success(editing ? "Job updated." : "Job created.");
      navigate("/recruiter/jobs");
    } catch (err) {
      const msg = errorMessage(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="max-w-3xl space-y-5 rounded-2xl border border-slate-200 bg-white p-6">
      {error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

      <Field id="title" label="Job title">
        <input id="title" value={v.title} onChange={set("title")} className={input} />
      </Field>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field id="company" label="Company (optional)" hint="Leave empty to use the company in your profile.">
          <input id="company" value={v.company} onChange={set("company")} className={input} />
        </Field>
        <Field id="location" label="Location">
          <input id="location" value={v.location} onChange={set("location")} className={input} />
        </Field>
      </div>

      <Field id="description" label="Description" hint="This text is turned into an embedding for semantic matching, so be specific (30+ characters).">
        <textarea id="description" rows={7} value={v.description} onChange={set("description")} className={input} />
      </Field>

      <Field id="skills" label="Required skills" hint="Separate skills with commas, for example: Python, SQL, Machine Learning.">
        <input id="skills" value={v.skills} onChange={set("skills")} className={input} />
      </Field>

      <div className="grid gap-5 sm:grid-cols-3">
        <Field id="jobType" label="Job type">
          <select id="jobType" value={v.jobType} onChange={set("jobType")} className={input}>
            {JOB_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </Field>
        <Field id="exp" label="Minimum experience (years)" hint="0 means freshers are welcome.">
          <input id="exp" type="number" min={0} max={40} value={v.requiredExperience} onChange={set("requiredExperience")} className={input} />
        </Field>
        <Field id="edu" label="Required education (optional)">
          <input id="edu" value={v.requiredEducation} onChange={set("requiredEducation")} className={input} />
        </Field>
      </div>

      <Field id="salary" label="Salary range (optional)">
        <input id="salary" value={v.salaryRange} onChange={set("salaryRange")} className={input} />
      </Field>

      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" checked={v.isActive} onChange={(e) => setV({ ...v, isActive: e.target.checked })} />
        Published (visible to candidates)
      </label>

      <div className="flex gap-3">
        <button disabled={busy} className="rounded-lg bg-navy-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-800 disabled:opacity-60">
          {busy ? "Saving…" : editing ? "Save changes" : "Create job"}
        </button>
        <button type="button" onClick={() => navigate("/recruiter/jobs")} className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-semibold text-navy-900 hover:bg-slate-50">
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function JobEditor() {
  const { id } = useParams();
  const { data, loading, error, reload } = useAsync(
    () => (id ? getManagedJob(id) : Promise.resolve(null)),
    [id]
  );

  if (loading) return <Spinner label="Loading job…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <>
      <PageHeader
        title={id ? "Edit Job" : "Create Job"}
        subtitle={id ? "Changing the title, description, skills, experience or education re-processes the job's embedding." : "Describe the role. Candidates are matched by meaning, not keywords."}
      />
      <JobForm key={id ?? "new"} job={data} />
    </>
  );
}