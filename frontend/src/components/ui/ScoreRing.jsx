export default function ScoreRing({ value, size = 72 }) {
  const r = (size - 10) / 2;
  const c = 2 * Math.PI * r;
  const v = value == null ? 0 : Math.max(0, Math.min(100, value));

  return (
    <div className="relative inline-flex shrink-0 items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth="6" />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-brand-600)" strokeWidth="6"
          strokeLinecap="round" strokeDasharray={`${(v / 100) * c} ${c}`}
        />
      </svg>
      <span className="absolute text-sm font-bold text-navy-900">{value == null ? "–" : `${value}%`}</span>
    </div>
  );
}