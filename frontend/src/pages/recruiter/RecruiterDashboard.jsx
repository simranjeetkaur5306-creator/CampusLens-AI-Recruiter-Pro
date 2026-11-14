import { Link } from "react-router-dom";
import { Briefcase, CheckCircle2, ClipboardList, Hourglass, XCircle } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import { EmptyState, ErrorState, InlineError, Spinner } from "../../components/ui/States";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { getApplicants, getManagedJobs } from "../../services/recruiterApi";
import { formatDate } from "../../utils/format";
import { statusLabel, statusStyle } from "../../utils/status";

async function load() {
  const [jobs, apps] = await Promise.allSettled([getManagedJobs(), getApplicants()]);
  const pick = (r) =>
    r.status === "fulfilled" ? { data: r.value, error: null } : { data: null, error: errorMessage(r.reason) };
  return { jobs: pick(jobs), apps: pick(apps) };
}

function Stat({ icon: Icon, label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">{label}</p>
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
          <Icon size={18} />
        </span>
      </div>
      <p className="mt-3 text-2xl font-bold text-navy-900">{value}</p>
    </div>
  );
}

function Card({ title, link, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-semibold text-navy-900">{title}</h2>
        {link && <Link to={link[0]} className="text-sm font-medium text-brand-700 hover:underline">{link[1]}</Link>}
      </div>
      {children}
    </section>
  );
}

export default function RecruiterDashboard() {
  const { data, loading, error, reload } = useAsync(load, []);

  if (loading) return <Spinner label="Loading your workspace…" />;
  if (error || !data) return <ErrorState message={error} onRetry={reload} />;

  const jobs = data.jobs.data ?? [];
  const apps = data.apps.data ?? [];
  const countBy = (s) => apps.filter((a) => a.status === s).length;

  const statusCounts = apps.reduce((acc, a) => {
    acc[a.status] = (acc[a.status] || 0) + 1;
    return acc;
  }, {});
  const perJob = apps.reduce((acc, a) => {
    acc[String(a.jobId)] = (acc[String(a.jobId)] || 0) + 1;
    return acc;
  }, {});
  const recent = apps.slice(0, 5); // the API already returns newest first

  return (
    <>
      <PageHeader
        title="Recruitment overview"
        subtitle="Live numbers from your jobs and applicants."
        actions={
          <Link to="/recruiter/jobs/new" className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">
            Create job
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Stat icon={Briefcase} label="Jobs posted" value={data.jobs.error ? "—" : jobs.length} />
        <Stat icon={CheckCircle2} label="Published jobs" value={data.jobs.error ? "—" : jobs.filter((j) => j.isActive).length} />
        <Stat icon={ClipboardList} label="Applications" value={data.apps.error ? "—" : apps.length} />
        <Stat icon={Hourglass} label="Awaiting review" value={data.apps.error ? "—" : countBy("applied")} />
        <Stat icon={XCircle} label="Shortlisted / rejected" value={data.apps.error ? "—" : `${countBy("shortlisted")} / ${countBy("rejected")}`} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="Your jobs" link={["/recruiter/jobs", "Manage"]}>
          {data.jobs.error ? (
            <InlineError what="jobs" message={data.jobs.error} />
          ) : jobs.length === 0 ? (
            <EmptyState
              icon={Briefcase}
              title="No jobs yet"
              text="Create your first job posting to start receiving ranked applicants."
              action={<Link to="/recruiter/jobs/new" className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">Create job</Link>}
            />
          ) : (
            <ul className="divide-y divide-slate-100">
              {jobs.slice(0, 5).map((j) => (
                <li key={j.id} className="flex items-center justify-between gap-3 py-3">
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-navy-900">{j.title}</span>
                    <span className="block text-xs text-slate-500">{perJob[String(j.id)] ?? 0} applicant(s)</span>
                  </span>
                  <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium ${j.isActive ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                    {j.isActive ? "Published" : "Unpublished"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Recent applicants" link={["/recruiter/applicants", "View all"]}>
          {data.apps.error ? (
            <InlineError what="applicants" message={data.apps.error} />
          ) : recent.length === 0 ? (
            <p className="text-sm text-slate-500">No applications yet.</p>
          ) : (
            <>
              <div className="mb-4 flex flex-wrap gap-2">
                {Object.entries(statusCounts).map(([s, n]) => (
                  <span key={s} className={`rounded-full px-3 py-1 text-xs font-medium ${statusStyle(s)}`}>
                    {statusLabel(s)}: {n}
                  </span>
                ))}
              </div>
              <ul className="divide-y divide-slate-100">
                {recent.map((a) => (
                  <li key={a.id}>
                    <Link to={`/recruiter/applicants/${a.id}`} className="block py-3 hover:bg-slate-50">
                      <span className="block truncate font-medium text-navy-900">{a.name}</span>
                      <span className="block truncate text-xs text-slate-500">{a.jobTitle} · {formatDate(a.appliedAt)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      </div>
    </>
  );
}