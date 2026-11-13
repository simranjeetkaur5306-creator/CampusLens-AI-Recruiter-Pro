import { Link } from "react-router-dom";
import { Activity, ArrowRight, Briefcase, LayoutDashboard, ListOrdered, Users } from "lucide-react";
import SampleBadge from "../ui/SampleBadge";

// All numbers below are illustrative sample data, not real results.
const stats = [["Open roles", "12"], ["Applicants", "248"], ["Avg. match", "74%"], ["Interviews", "9"]];
const bars = [40, 62, 48, 80, 66, 90, 72];
const rows = [["Candidate A", 92], ["Candidate B", 85], ["Candidate C", 78]];
const nav = [
  [LayoutDashboard, "Overview"], [Briefcase, "Jobs"], [Users, "Applicants"], [ListOrdered, "Ranking"], [Activity, "Analytics"],
];

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_50%_0%,var(--color-brand-100),transparent)]" />
      <div className="relative mx-auto max-w-7xl px-4 pb-20 pt-16 sm:px-6 lg:px-8 lg:pt-24">
        <div className="mx-auto max-w-4xl text-center">
          <p className="inline-block rounded-full border border-brand-200 bg-white px-3 py-1 text-xs font-semibold text-brand-700">
            AI-powered recruitment and career intelligence
          </p>
          <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-navy-900 sm:text-5xl lg:text-6xl">
            Talent intelligence that understands <span className="text-brand-600">meaning</span>, not just keywords.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-600">
            CampusLens AI reads resumes, matches them to roles with semantic embeddings, ranks candidates,
            explains skill gaps and prepares interviews, so people make better hiring decisions faster.
          </p>
          <div className="mt-9 flex flex-wrap justify-center gap-3">
            <Link to="/register/candidate" className="inline-flex items-center gap-2 rounded-xl bg-navy-900 px-6 py-3.5 font-semibold text-white shadow-lg shadow-navy-900/20 hover:bg-navy-800">
              Start as a candidate <ArrowRight size={18} />
            </Link>
            <Link to="/register/recruiter" className="rounded-xl border border-slate-300 bg-white px-6 py-3.5 font-semibold text-navy-900 hover:bg-slate-50">
              Hire as a recruiter
            </Link>
          </div>
        </div>

        <div className="mx-auto mt-16 max-w-5xl">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl shadow-navy-900/10">
            <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-4 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
              <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
              <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
              <SampleBadge className="ml-auto" />
            </div>
            <div className="grid md:grid-cols-[180px_1fr]">
              <aside className="hidden border-r border-slate-100 bg-navy-900 p-4 md:block">
                <ul className="space-y-1">
                  {nav.map(([Icon, label], i) => (
                    <li key={label} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${i === 0 ? "bg-white/10 text-white" : "text-slate-400"}`}>
                      <Icon size={16} /> {label}
                    </li>
                  ))}
                </ul>
              </aside>
              <div className="p-5">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {stats.map(([label, value]) => (
                    <div key={label} className="rounded-xl border border-slate-200 p-3">
                      <p className="text-xs text-slate-500">{label}</p>
                      <p className="mt-1 text-xl font-bold text-navy-900">{value}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 p-4">
                    <p className="text-sm font-semibold text-navy-900">Applications per week</p>
                    <div className="mt-4 flex h-28 items-end gap-2">
                      {bars.map((h, i) => (
                        <div key={i} className="flex-1 rounded-t-md bg-brand-500/80" style={{ height: `${h}%` }} />
                      ))}
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-200 p-4">
                    <p className="text-sm font-semibold text-navy-900">Top ranked candidates</p>
                    <ul className="mt-3 space-y-3">
                      {rows.map(([name, score]) => (
                        <li key={name}>
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-700">{name}</span>
                            <span className="font-semibold text-brand-700">{score}%</span>
                          </div>
                          <div className="mt-1 h-1.5 rounded-full bg-slate-100">
                            <div className="h-1.5 rounded-full bg-navy-800" style={{ width: `${score}%` }} />
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}