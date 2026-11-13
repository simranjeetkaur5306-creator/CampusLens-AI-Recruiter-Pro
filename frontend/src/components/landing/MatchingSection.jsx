import { ArrowDown, Check } from "lucide-react";
import Reveal from "../ui/Reveal";
import SampleBadge from "../ui/SampleBadge";

const points = [
  "PDF and DOCX resumes parsed into skills, education, experience and projects",
  "Resumes and job descriptions converted into dense vector embeddings",
  "Cosine similarity computed with pgvector for meaning-based matching",
  "Match scores shown with matching and missing skills, not a black box",
];

export default function MatchingSection() {
  return (
    <section id="matching" className="scroll-mt-20 py-24">
      <div className="mx-auto grid max-w-7xl items-center gap-14 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
        <Reveal>
          <p className="text-sm font-semibold uppercase tracking-wider text-brand-600">Resume intelligence</p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-navy-900 sm:text-4xl">
            From unstructured resumes to semantic understanding
          </h2>
          <p className="mt-4 text-slate-600">
            Keyword filters miss people whose wording differs from the job description. CampusLens compares
            what resumes and roles actually mean.
          </p>
          <ul className="mt-6 space-y-3">
            {points.map((p) => (
              <li key={p} className="flex gap-3 text-sm text-slate-700">
                <Check size={18} className="mt-0.5 shrink-0 text-brand-600" /> {p}
              </li>
            ))}
          </ul>
        </Reveal>

        <Reveal delay={120}>
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-navy-900/5">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-navy-900">Matching pipeline</h3>
              <SampleBadge />
            </div>
            <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
              <p className="font-medium text-navy-900">Resume</p>
              <p className="mt-1 text-slate-600">Built a churn prediction model with Python and scikit-learn…</p>
            </div>
            <div className="my-2 flex justify-center text-brand-500"><ArrowDown size={18} /></div>
            <div className="rounded-xl border border-brand-200 bg-brand-50 p-4 font-mono text-xs text-brand-800">
              embedding = [0.12, −0.48, 0.33, 0.07, …]
            </div>
            <div className="my-2 flex justify-center text-brand-500"><ArrowDown size={18} /></div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
              <p className="font-medium text-navy-900">Job description</p>
              <p className="mt-1 text-slate-600">Data analyst skilled in machine learning and predictive modelling…</p>
            </div>
            <div className="mt-5 rounded-xl bg-navy-900 p-4 text-white">
              <p className="font-mono text-xs text-brand-300">cos(θ) = (A · B) / (‖A‖ ‖B‖)</p>
              <div className="mt-3 flex items-center justify-between text-sm">
                <span>Semantic similarity</span>
                <span className="font-semibold">0.87</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-white/15">
                <div className="h-2 rounded-full bg-brand-400" style={{ width: "87%" }} />
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}