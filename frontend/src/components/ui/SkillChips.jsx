const TONES = {
  neutral: "bg-slate-100 text-slate-700",
  brand: "bg-brand-50 text-brand-700",
  matched: "bg-emerald-50 text-emerald-700",
  partial: "bg-amber-50 text-amber-700",
  missing: "bg-rose-50 text-rose-700",
};

export default function SkillChips({ skills = [], tone = "brand", empty = "None detected", limit }) {
  if (!skills.length) return <p className="text-sm text-slate-400">{empty}</p>;
  const shown = limit ? skills.slice(0, limit) : skills;
  return (
    <div className="flex flex-wrap gap-1.5">
      {shown.map((s) => (
        <span key={s} className={`rounded-md px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>{s}</span>
      ))}
      {limit && skills.length > limit && (
        <span className="px-1 py-0.5 text-xs text-slate-500">+{skills.length - limit} more</span>
      )}
    </div>
  );
}