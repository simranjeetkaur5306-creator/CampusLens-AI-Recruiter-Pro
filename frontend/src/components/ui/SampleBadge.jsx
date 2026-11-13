export default function SampleBadge({ className = "" }) {
  return (
    <span className={`inline-block rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700 ${className}`}>
      Sample data · illustration only
    </span>
  );
}