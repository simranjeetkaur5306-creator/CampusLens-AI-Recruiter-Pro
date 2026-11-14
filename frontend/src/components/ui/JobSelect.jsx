export default function JobSelect({ options, value, onChange, label = "Job" }) {
  const list = [...options];
  if (value && !list.some((o) => String(o.id) === String(value))) {
    list.push({ id: value, title: `Job #${value}`, company: "" });
  }
  return (
    <div>
      <label htmlFor="job-select" className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
      <select
        id="job-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden"
      >
        <option value="">Select a job…</option>
        {list.map((o) => (
          <option key={o.id} value={String(o.id)}>
            {o.title}{o.company ? ` · ${o.company}` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}