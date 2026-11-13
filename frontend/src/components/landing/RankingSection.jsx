import Reveal from "../ui/Reveal";
import SampleBadge from "../ui/SampleBadge";

const rows = [
  { rank: 1, name: "Candidate A", score: 92, matched: ["Python", "SQL", "Machine Learning"], missing: [] },
  { rank: 2, name: "Candidate B", score: 85, matched: ["Python", "SQL"], missing: ["Deep Learning"] },
  { rank: 3, name: "Candidate C", score: 78, matched: ["Python"], missing: ["SQL", "Deep Learning"] },
];

export default function RankingSection() {
  return (
    <section id="ranking" className="scroll-mt-20 bg-slate-50 py-24">
      <div className="mx-auto grid max-w-7xl items-center gap-14 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
        <Reveal className="lg:order-2">
          <p className="text-sm font-semibold uppercase tracking-wider text-brand-600">Candidate ranking</p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-navy-900 sm:text-4xl">
            Review the strongest matches first
          </h2>
          <p className="mt-4 text-slate-600">
            Every job gets a ranked applicant list with match scores, matching skills and missing skills.
            Recruiters shortlist, reject and schedule interviews from the same view.
          </p>
          <p className="mt-4 rounded-xl border border-brand-200 bg-brand-50 p-4 text-sm text-brand-900">
            Ranking is decision support. A person always makes the final hiring decision.
          </p>
        </Reveal>

        <Reveal delay={120} className="lg:order-1">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xl shadow-navy-900/5">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-navy-900">Data Analyst · Applicants</h3>
              <SampleBadge />
            </div>
            <ul className="mt-4 divide-y divide-slate-100">
              {rows.map((r) => (
                <li key={r.rank} className="py-4">
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-navy-900 text-sm font-bold text-white">{r.rank}</span>
                    <span className="flex-1 font-medium text-navy-900">{r.name}</span>
                    <span className="text-lg font-bold text-brand-700">{r.score}%</span>
                  </div>
                  <div className="mt-2 h-1.5 rounded-full bg-slate-100">
                    <div className="h-1.5 rounded-full bg-brand-600" style={{ width: `${r.score}%` }} />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {r.matched.map((s) => (
                      <span key={s} className="rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">{s}</span>
                    ))}
                    {r.missing.map((s) => (
                      <span key={s} className="rounded-md bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700">Missing: {s}</span>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </Reveal>
      </div>
    </section>
  );
}