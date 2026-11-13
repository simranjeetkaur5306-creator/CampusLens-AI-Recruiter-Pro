import { Eye, Lock, Scale, ShieldCheck } from "lucide-react";
import Reveal from "../ui/Reveal";

const items = [
  { icon: ShieldCheck, title: "Human in the loop", text: "Scores and rankings assist reviewers. They are never an automatic hiring decision." },
  { icon: Eye, title: "Explainable results", text: "Matched and missing skills are shown next to every score." },
  { icon: Lock, title: "Secure by design", text: "JWT authentication, role-based access and server-side API keys that never reach the browser." },
  { icon: Scale, title: "Honest limitations", text: "Pretrained models can carry bias and scanned resumes may parse poorly. We state this openly." },
];

export default function ResponsibleAI() {
  return (
    <section id="responsible-ai" className="scroll-mt-20 py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-brand-600">Responsible AI</p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-navy-900 sm:text-4xl">Trustworthy AI for hiring decisions</h2>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {items.map(({ icon: Icon, title, text }, i) => (
            <Reveal key={title} delay={i * 90}>
              <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700"><Icon size={22} /></span>
                <h3 className="mt-4 font-semibold text-navy-900">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}