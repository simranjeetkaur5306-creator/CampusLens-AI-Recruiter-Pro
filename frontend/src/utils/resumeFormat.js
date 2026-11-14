const text = (v) => (typeof v === "string" ? v.trim() : typeof v === "number" ? String(v) : "");
const list = (v) => (Array.isArray(v) ? v.map(text).filter(Boolean) : text(v) ? [text(v)] : []);

// The resume parser stores education/experience/projects as JSON objects. These turn them into display text.
export function formatEducation(item) {
  if (typeof item === "string") return item;
  const years = list(item?.years).join("–");
  return [text(item?.degree), text(item?.institution), years, text(item?.grade)].filter(Boolean).join(" · ");
}

export function formatExperience(item) {
  if (typeof item === "string") return { title: item, sub: "", bullets: [] };
  return {
    title: text(item?.title) || "Experience",
    sub: [text(item?.organization), text(item?.duration)].filter(Boolean).join(" · "),
    bullets: list(item?.description),
  };
}

export function formatProject(item) {
  if (typeof item === "string") return { title: item, tech: [], bullets: [] };
  return {
    title: text(item?.title) || "Project",
    tech: list(item?.technologies),
    bullets: list(item?.description),
  };
}

export const isHttpUrl = (u) => typeof u === "string" && /^https?:\/\//i.test(u);