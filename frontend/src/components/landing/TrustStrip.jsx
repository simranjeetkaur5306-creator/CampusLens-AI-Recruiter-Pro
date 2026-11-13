const items = ["React", "Django REST Framework", "PostgreSQL + pgvector", "Sentence embeddings", "JWT security", "LLM-assisted insights"];

export default function TrustStrip() {
  return (
    <section className="border-y border-slate-200 bg-slate-50">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <p className="text-center text-xs font-semibold uppercase tracking-wider text-slate-500">Built on a modern AI stack</p>
        <ul className="mt-3 flex flex-wrap justify-center gap-x-8 gap-y-2 text-sm font-medium text-navy-700">
          {items.map((i) => <li key={i}>{i}</li>)}
        </ul>
      </div>
    </section>
  );
}