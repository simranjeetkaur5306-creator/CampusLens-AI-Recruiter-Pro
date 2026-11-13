import { useState } from "react";
import Reveal from "../ui/Reveal";
import SampleBadge from "../ui/SampleBadge";

const sets = {
  Technical: [
    "How would you handle class imbalance when training a classifier?",
    "Write a SQL query to find the top three products by monthly revenue.",
  ],
  Conceptual: [
    "Explain the bias–variance trade-off.",
    "Why is cosine similarity often used to compare text embeddings?",
  ],
  "Project-based": [
    "Walk us through a project where you used Python for data analysis. What was your contribution?",
    "What would you change if you rebuilt that project today?",
  ],
  HR: [
    "Why are you interested in this role?",
    "Tell us about a time you acted on critical feedback.",
  ],
};

export default function InterviewSection() {
  const tabs = Object.keys(sets);
  const [active, setActive] = useState(tabs[0]);

  return (
    <section id="interview" className="scroll-mt-20 py-24">
      <div className="mx-auto grid max-w-7xl items-center gap-14 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
        <Reveal>
          <p className="text-sm font-semibold uppercase tracking-wider text-brand-600">AI interview preparation</p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-navy-900 sm:text-4xl">
            Interview questions tailored to the role and the person
          </h2>
          <p className="mt-4 text-slate-600">
            An LLM generates technical, conceptual, project-based and HR questions from the job description,
            required skills and the candidate&apos;s structured profile. If the AI service is unavailable,
            the app clearly labels template questions instead of failing.
          </p>
        </Reveal>

        <Reveal delay={120}>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xl shadow-navy-900/5">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-navy-900">Generated questions</h3>
              <SampleBadge />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {tabs.map((t) => (
                <button
                  key={t}
                  onClick={() => setActive(t)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    active === t ? "bg-navy-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
            <ol className="mt-5 space-y-3">
              {sets[active].map((q, i) => (
                <li key={q} className="flex gap-3 rounded-xl border border-slate-200 p-4 text-sm text-slate-700">
                  <span className="font-bold text-brand-600">{i + 1}.</span> {q}
                </li>
              ))}
            </ol>
          </div>
        </Reveal>
      </div>
    </section>
  );
}