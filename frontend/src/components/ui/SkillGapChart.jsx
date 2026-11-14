import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const COLORS = { Matched: "#059669", Partial: "#d97706", Missing: "#e11d48" };

export default function SkillGapChart({ matched, partial, missing }) {
  const data = [
    { name: "Matched", value: matched },
    { name: "Partial", value: partial },
    { name: "Missing", value: missing },
  ].filter((d) => d.value > 0);

  if (data.length === 0) return null;

  return (
    <div className="h-52 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={48} outerRadius={80} paddingAngle={2}>
            {data.map((d) => <Cell key={d.name} fill={COLORS[d.name]} />)}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}