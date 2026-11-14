import { useState } from "react";

const DIFFICULTY = {
  easy: "bg-emerald-50 text-emerald-700",
  medium: "bg-amber-50 text-amber-700",
  hard: "bg-rose-50 text-rose-700",
};

// Displays a normalized interview question set (see services/questionSet.js) in category tabs.
export default function QuestionSections({ set }) {
  const [tab, setTab] = useState(set.sections[0]?.key ?? "");
  const section = set.sections.find((s) => s.key === tab) ?? set.sections[0];

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {set.sections.map((s) => (
          <button
            key={s.key}
            onClick={() => setTab(s.key)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              section?.key === s.key ? "bg-navy-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {s.label} ({s.items.length})
          </button>
        ))}
      </div>

      {!section || section.items.length === 0 ? (
        <p className="mt-5 text-sm text-slate-500">No questions in this category.</p>
      ) : (
        <ol className="mt-5 space-y-3">
          {section.items.map((q, i) => (
            <li key={i} className="rounded-xl border border-slate-200 p-4 text-sm">
              <p className="text-slate-800"><span className="mr-2 font-bold text-brand-600">{i + 1}.</span>{q.question}</p>
              {(q.skill || q.difficulty) && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {q.skill && <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{q.skill}</span>}
                  {q.difficulty && (
                    <span className={`rounded-md px-2 py-0.5 text-xs font-medium ${DIFFICULTY[q.difficulty] ?? "bg-slate-100 text-slate-600"}`}>
                      {q.difficulty}
                    </span>
                  )}
                </div>
              )}
              {q.answerGuide && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs font-semibold text-brand-700">Answer guide</summary>
                  <p className="mt-1 text-xs leading-relaxed text-slate-600">{q.answerGuide}</p>
                </details>
              )}
            </li>
          ))}
        </ol>
      )}
      {set.note && <p className="mt-4 text-xs text-slate-500">{set.note}</p>}
    </div>
  );
}