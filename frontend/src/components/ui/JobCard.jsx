import { Link } from "react-router-dom";
import { MapPin } from "lucide-react";
import ScoreRing from "./ScoreRing";
import SkillChips from "./SkillChips";

export default function JobCard({ job, applied, applying, onApply }) {
  const hasMatchInfo = job.matchedSkills.length > 0 || job.missingSkills.length > 0;

  return (
    <article className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 transition hover:shadow-md">
      <div className="flex items-start gap-4">
        <ScoreRing value={job.matchScore} size={64} />
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold text-navy-900">{job.title}</h3>
          <p className="truncate text-sm text-slate-500">{job.company || "Company not specified"}</p>
          {job.location && (
            <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
              <MapPin size={12} /> {job.location}
            </p>
          )}
        </div>
      </div>

      <div className="mt-4 flex-1 space-y-3">
        {hasMatchInfo ? (
          <>
            {job.matchedSkills.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Matched</p>
                <SkillChips skills={job.matchedSkills} tone="matched" limit={5} />
              </div>
            )}
            {job.missingSkills.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Missing</p>
                <SkillChips skills={job.missingSkills} tone="missing" limit={4} />
              </div>
            )}
          </>
        ) : (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Required skills</p>
            <SkillChips skills={job.requiredSkills} tone="brand" limit={6} empty="Not specified" />
          </div>
        )}
      </div>

      <div className="mt-5 flex gap-2">
        <Link
          to={`/candidate/jobs/${job.id}`}
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-center text-sm font-semibold text-navy-900 hover:bg-slate-50"
        >
          View details
        </Link>
        <button
          onClick={() => onApply(job)}
          disabled={applied || applying}
          className="flex-1 rounded-lg bg-navy-900 px-3 py-2 text-sm font-semibold text-white hover:bg-navy-800 disabled:opacity-60"
        >
          {applied ? "Applied" : applying ? "Applying…" : "Apply"}
        </button>
      </div>
    </article>
  );
}