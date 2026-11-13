import { Check } from "lucide-react";
import Reveal from "../ui/Reveal";

const candidates = [
  "Resume upload with extracted skills, education and experience",
  "AI job recommendations with match percentage",
  "Matched, partial and missing skills for every role",
  "Skill-gap analysis with learning suggestions",
  "AI interview preparation by job",
  "Application tracking and email updates",
];
const recruiters = [
  "Create, edit and publish job postings",
  "Ranked applicants with explainable match scores",
  "Candidate profiles and resume preview",
  "Skill-based candidate comparison",
  "Shortlist, reject and schedule interviews",
  "Analytics calculated from real hiring data",
];

function Column({ title, subtitle, items, dark }) {
  return (
    <div className={`h-full rounded-2xl p-8 ${dark ? "bg-navy-900 text-white" : "border border-slate-200 bg-white"}`}>
      <h3 className={`text-xl font-bold ${dark ? "text-white" : "text-navy-900"}`}>{title}</h3>
      <p className={`mt-1 text-sm ${dark ? "text-slate-300" : "text-slate-500"}`}>{subtitle}</p>
      <ul className="mt-6 space-y-3">
        {items.map((i) => (
          <li key={i} className="flex gap-3 text-sm">
            <Check size={18} className={`mt-0.5 shrink-0 ${dark ? "text-brand-300" : "text-brand-600"}`} />
            <span className={dark ? "text-slate-200" : "text-slate-700"}>{i}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Features() {
  return (
    <section id="features" className="scroll-mt-20 bg-slate-50 py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-brand-600">Platform</p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-navy-900 sm:text-4xl">One platform, two focused workspaces</h2>
        </div>
        <div className="mt-12 grid gap-6 lg:grid-cols-2">
          <Reveal><Column title="For candidates" subtitle="Understand your fit and prepare with confidence." items={candidates} /></Reveal>
          <Reveal delay={120}><Column dark title="For recruiters" subtitle="Screen faster with explainable AI assistance." items={recruiters} /></Reveal>
        </div>
      </div>
    </section>
  );
}