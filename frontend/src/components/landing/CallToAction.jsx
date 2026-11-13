import { Link } from "react-router-dom";
import Reveal from "../ui/Reveal";

export default function CallToAction() {
  return (
    <section className="px-4 pb-24 sm:px-6 lg:px-8">
      <Reveal>
        <div className="mx-auto max-w-7xl overflow-hidden rounded-3xl bg-navy-900 px-6 py-16 text-center text-white">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">See semantic hiring in action</h2>
          <p className="mx-auto mt-4 max-w-xl text-slate-300">
            Create a candidate or recruiter account and explore the complete workflow.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/register/candidate" className="rounded-xl bg-white px-6 py-3.5 font-semibold text-navy-900 hover:bg-brand-50">Join as candidate</Link>
            <Link to="/register/recruiter" className="rounded-xl border border-white/30 px-6 py-3.5 font-semibold text-white hover:bg-white/10">Join as recruiter</Link>
          </div>
        </div>
      </Reveal>
    </section>
  );
}