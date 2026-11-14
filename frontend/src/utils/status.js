const STYLES = {
  applied: "bg-slate-100 text-slate-700",
  under_review: "bg-brand-50 text-brand-700",
  shortlisted: "bg-emerald-50 text-emerald-700",
  interview_scheduled: "bg-violet-50 text-violet-700",
  rejected: "bg-rose-50 text-rose-700",
};

export const statusStyle = (s) =>
  STYLES[String(s || "").toLowerCase()] ?? "bg-slate-100 text-slate-700";

export const statusLabel = (s) =>
  String(s || "applied").replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());