const LABELS = {
  full_time: "Full-time",
  part_time: "Part-time",
  internship: "Internship",
  contract: "Contract",
  freelance: "Freelance",
};

export const jobTypeLabel = (value) => LABELS[value] ?? (value ? String(value).replace(/_/g, " ") : "");

export const experienceLabel = (years) =>
  Number(years) > 0 ? `${years}+ yr experience` : "Freshers welcome";