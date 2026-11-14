import { Link } from "react-router-dom";
import { Briefcase, ClipboardList, FileText, Sparkles } from "lucide-react";
import PageHeader from "../../components/ui/PageHeader";
import ScoreRing from "../../components/ui/ScoreRing";
import SkillChips from "../../components/ui/SkillChips";
import { EmptyState, ErrorState, InlineError, Spinner } from "../../components/ui/States";
import { useAuth } from "../../context/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { getApplications, getRecommendations, getResumes } from "../../services/candidateApi";
import { formatDate } from "../../utils/format";
import { statusLabel, statusStyle } from "../../utils/status";

async function fetchDashboard() {
  const [resumes, recs, apps] = await Promise.allSettled([
    getResumes(),
    getRecommendations(),
    getApplications(),
  ]);
  const pick = (r) =>
    r.status === "fulfilled"
      ? { data: r.value, error: null }
      : { data: null, error: errorMessage(r.reason) };
  return { resumes: pick(resumes), recs: pick(recs), apps: pick(apps) };
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

export default function CandidateDashboard() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useAsync(fetchDashboard, []);

  if (loading) return <Spinner label="Loading your dashboard…" />;
  if (error || !data) return <ErrorState message={error} onRetry={reload} />;

  const { resumes, recs, apps } = data;
  const resume = resumes.data?.[0] ?? null;
  const recList = recs.data ?? [];
  const appList = apps.data ?? [];

  const scores = recList.map((r) => r.matchScore).filter((s) => s != null);
  const best = scores.length ? Math.max(...scores) : null;
  const topRecs = [...recList].sort((a, b) => (b.matchScore ?? -1) - (a.matchScore ?? -1)).slice(0, 3);
  const recentApps = [...appList]
    .sort((a, b) => new Date(b.appliedAt || 0) - new Date(a.appliedAt || 0))
    .slice(0, 4);
  const statusCounts = appList.reduce((acc, a) => {
    acc[a.status] = (acc[a.status] || 0) + 1;
    return acc;
  }, {});

  const name = user?.full_name ?? user?.first_name ?? user?.email ?? "";

  return (
    <>
      <PageHeader title={`Welcome back${name ? `, ${name}` : ""}`} subtitle="Your resume, matches and applications at a glance." />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat icon={FileText} label="Resume" value={resumes.error ? "—" : resume ? `${resume.skills.length} skills` : "Not uploaded"} />
        <Stat icon={Sparkles} label="Recommended jobs" value={recs.error ? "—" : recList.length} />
        <Stat icon={Briefcase} label="Best match" value={best != null ? `${best}%` : "—"} />
        <Stat icon={ClipboardList} label="Applications" value={apps.error ? "—" : appList.length} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="Resume" link={resume ? ["/candidate/resume-analysis", "View analysis"] : null}>
          {resumes.error ? (
            <InlineError what="resumes" message={resumes.error} />
          ) : !resume ? (
            <EmptyState
              icon={FileText}
              title="No resume yet"
              text="Upload a PDF or DOCX resume to get skills extracted and job matches."
              action={<Link to="/candidate/resume-upload" className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">Upload resume</Link>}
            />
          ) : (
            <>
              <p className="text-sm font-medium text-navy-900">{resume.fileName}</p>
              <p className="text-xs text-slate-500">Uploaded {formatDate(resume.uploadedAt)}</p>
              <div className="mt-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Extracted skills</p>
                <SkillChips skills={resume.skills} limit={12} />
              </div>
            </>
          )}
        </Card>

        <Card title="Top job matches" link={["/candidate/recommendations", "See all"]}>
          {recs.error ? (
            <InlineError what="recommendations" message={recs.error} />
          ) : topRecs.length === 0 ? (
            <p className="text-sm text-slate-500">No recommendations yet. Upload a resume and publish jobs exist to see matches.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {topRecs.map((j) => (
                <li key={j.id}>
                  <Link to={`/candidate/jobs/${j.id}`} className="flex items-center gap-4 py-3 hover:bg-slate-50">
                    <ScoreRing value={j.matchScore} size={56} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium text-navy-900">{j.title}</span>
                      <span className="block truncate text-xs text-slate-500">{j.company || "Company not specified"}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="lg:col-span-2">
          <Card title="Recent applications" link={["/candidate/applications", "View all"]}>
            {apps.error ? (
              <InlineError what="applications" message={apps.error} />
            ) : recentApps.length === 0 ? (
              <p className="text-sm text-slate-500">You have not applied to any jobs yet.</p>
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
                  {recentApps.map((a) => (
                    <li key={a.id} className="flex items-center justify-between gap-3 py-3">
                      <span className="min-w-0">
                        <span className="block truncate font-medium text-navy-900">{a.jobTitle}</span>
                        <span className="block text-xs text-slate-500">Applied {formatDate(a.appliedAt)}</span>
                      </span>
                      <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium ${statusStyle(a.status)}`}>
                        {statusLabel(a.status)}
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}