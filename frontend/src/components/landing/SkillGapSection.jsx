import Reveal from "../ui/Reveal";
import SampleBadge from "../ui/SampleBadge";

// Illustrative example based on the project synopsis.
const required = ["Python", "SQL", "Machine Learning", "Deep Learning", "Statistics"];
const matched = ["Python", "SQL", "Machine Learning"];
const partial = ["Statistics"];
const missing = ["Deep Learning"];

const R = 52;
const C = 2 * Math.PI * R;

export default function SkillGapSection() {
  const pct = Math.round((matched.length / required.length) * 100);

  return (
    <section id="skill-gap" className="scroll-mt-20 bg-slate-50 py-24">
      <div className="mx-auto grid max-w-7xl items-center gap-14 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
        <Reveal className="lg:order-2">
          <p className="text-sm font-semibold uppercase tracking-wider text-brand-600">Skill-gap analysis</p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-navy-900 sm:text-4xl">
            Know exactly what to learn next
          </h2>
          <p className="mt-4 text-slate-600">
            Candidate skills are compared with role requirements using extracted data. The result is grounded in
            the resume, then summarised in plain language with practical learning suggestions.
          </p>
        </Reveal>

        <Reveal delay={120} className="lg:order-1">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-navy-900/5">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-navy-900">Skill coverage</h3>
              <SampleBadge />
            </div>
            <div className="mt-5 flex items-center gap-6">
              <svg viewBox="0 0 120 120" className="h-28 w-28 shrink-0 -rotate-90">
                <circle cx="60" cy="60" r={R} fill="none" stroke="#e2e8f0" strokeWidth="10" />
                <circle
                  cx="60" cy="60" r={R} fill="none" stroke="var(--color-brand-600)" strokeWidth="10"
                  strokeLinecap="round" strokeDasharray={`${(pct / 100) * C} ${C}`}
                />
              </svg>
              <div>
                <p className="text-3xl font-extrabold text-navy-900">{pct}%</p>
                <p className="text-sm text-slate-500">{matched.length} of {required.length} required skills matched</p>
              </div>
            </div>
            <div className="mt-5 space-y-3 text-sm">
              <div>
                <p className="mb-1.5 font-medium text-navy-900">Matched</p>
                <div className="flex flex-wrap gap-1.5">
                  {matched.map((s) => <span key={s} className="rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">{s}</span>)}
                </div>
              </div>
              <div>
                <p className="mb-1.5 font-medium text-navy-900">Partial</p>
                <div className="flex flex-wrap gap-1.5">
                  {partial.map((s) => <span key={s} className="rounded-md bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">{s}</span>)}
                </div>
              </div>
              <div>
                <p className="mb-1.5 font-medium text-navy-900">Missing</p>
                <div className="flex flex-wrap gap-1.5">
                  {missing.map((s) => <span key={s} className="rounded-md bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700">{s}</span>)}
                </div>
              </div>
            </div>
            <p className="mt-5 rounded-xl bg-brand-50 p-3 text-sm text-brand-900">
              Suggestion: study neural network fundamentals, then build a small image classifier project.
            </p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}