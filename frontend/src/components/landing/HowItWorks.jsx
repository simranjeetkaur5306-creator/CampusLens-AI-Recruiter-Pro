import { Brain, ListOrdered, Upload, UserCheck } from "lucide-react";
import Reveal from "../ui/Reveal";

const steps = [
  { icon: Upload, title: "Upload", text: "A candidate uploads a PDF or DOCX resume." },
  { icon: Brain, title: "Understand", text: "NLP extracts structure and embeddings capture meaning." },
  { icon: ListOrdered, title: "Match and rank", text: "pgvector cosine similarity scores and ranks jobs and candidates." },
  { icon: UserCheck, title: "Decide", text: "Recruiters review explanations and make the final call." },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-20 py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-brand-600">How it works</p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-navy-900 sm:text-4xl">From resume to decision in four steps</h2>
        </div>
        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map(({ icon: Icon, title, text }, i) => (
            <Reveal key={title} delay={i * 100}>
              <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
                <div className="flex items-center justify-between">
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-navy-900 text-white"><Icon size={20} /></span>
                  <span className="text-3xl font-extrabold text-slate-200">0{i + 1}</span>
                </div>
                <h3 className="mt-5 font-semibold text-navy-900">{title}</h3>
                <p className="mt-2 text-sm text-slate-600">{text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}