import SkillChips from "./SkillChips";
import { formatEducation, formatExperience, formatProject } from "../../utils/resumeFormat";

function Block({ title, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="font-semibold text-navy-900">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

const Empty = () => <p className="text-sm text-slate-400">Not detected</p>;

// Shows the parsed parts of a resume. `resume` uses plain skill-name strings.
export default function ResumeSections({ resume }) {
  const { skills = [], education = [], experience = [], projects = [], certifications = [] } = resume;

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Block title={`Skills (${skills.length})`}>
        <SkillChips skills={skills} />
      </Block>

      <Block title="Education">
        {education.length === 0 ? <Empty /> : (
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-700">
            {education.map((e, i) => <li key={i}>{formatEducation(e) || "—"}</li>)}
          </ul>
        )}
      </Block>

      <Block title="Experience">
        {experience.length === 0 ? <Empty /> : (
          <ul className="space-y-4">
            {experience.map((item, i) => {
              const x = formatExperience(item);
              return (
                <li key={i} className="text-sm">
                  <p className="font-medium text-navy-900">{x.title}</p>
                  {x.sub && <p className="text-xs text-slate-500">{x.sub}</p>}
                  {x.bullets.length > 0 && (
                    <ul className="mt-1 list-disc space-y-0.5 pl-5 text-slate-700">
                      {x.bullets.map((b, j) => <li key={j}>{b}</li>)}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </Block>

      <Block title="Projects">
        {projects.length === 0 ? <Empty /> : (
          <ul className="space-y-4">
            {projects.map((item, i) => {
              const p = formatProject(item);
              return (
                <li key={i} className="text-sm">
                  <p className="font-medium text-navy-900">{p.title}</p>
                  {p.tech.length > 0 && <div className="mt-1"><SkillChips skills={p.tech} tone="neutral" /></div>}
                  {p.bullets.length > 0 && (
                    <ul className="mt-1 list-disc space-y-0.5 pl-5 text-slate-700">
                      {p.bullets.map((b, j) => <li key={j}>{b}</li>)}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </Block>

      <Block title="Certifications">
        {certifications.length === 0 ? <Empty /> : (
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-700">
            {certifications.map((c, i) => <li key={i}>{typeof c === "string" ? c : formatEducation(c)}</li>)}
          </ul>
        )}
      </Block>
    </div>
  );
}