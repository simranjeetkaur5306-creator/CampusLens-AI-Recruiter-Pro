import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { errorMessage } from "../../services/api";
import { ENDPOINTS } from "../../services/endpoints";

const input =
  "w-full rounded-lg border border-slate-300 px-3 py-2.5 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-hidden";

export default function RegisterForm({ role }) {
  const isRecruiter = role === "recruiter";
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", company_name: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.full_name.trim()) return setError("Please enter your name.");
    if (!/^\S+@\S+\.\S+$/.test(form.email)) return setError("Please enter a valid email.");
    if (form.password.length < 8) return setError("Password must be at least 8 characters.");
    if (isRecruiter && !form.company_name.trim()) return setError("Please enter your company name.");

    // Adjust these field names to match your Phase 3/4 register serializers.
    const payload = {
      full_name: form.full_name.trim(),
      email: form.email.trim(),
      password: form.password,
      ...(isRecruiter ? { company_name: form.company_name.trim() } : {}),
    };

    setBusy(true);
    try {
      await api.post(isRecruiter ? ENDPOINTS.registerRecruiter : ENDPOINTS.registerCandidate, payload);
      navigate("/login", { state: { registered: true } });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-2xl font-bold tracking-tight">{isRecruiter ? "Recruiter" : "Candidate"} registration</h1>
      <p className="mt-1 text-sm text-slate-500">
        {isRecruiter ? "Post jobs and review AI-ranked candidates." : "Upload your resume and get matched to jobs."}
      </p>
      <form onSubmit={onSubmit} className="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <div>
          <label className="mb-1 block text-sm font-medium">Full name</label>
          <input value={form.full_name} onChange={set("full_name")} className={input} />
        </div>
        {isRecruiter && (
          <div>
            <label className="mb-1 block text-sm font-medium">Company name</label>
            <input value={form.company_name} onChange={set("company_name")} className={input} />
          </div>
        )}
        <div>
          <label className="mb-1 block text-sm font-medium">Email</label>
          <input type="email" value={form.email} onChange={set("email")} className={input} />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Password</label>
          <input type="password" autoComplete="new-password" value={form.password} onChange={set("password")} className={input} />
        </div>
        <button disabled={busy} className="w-full rounded-lg bg-indigo-600 py-2.5 font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600">
        Already registered? <Link to="/login" className="text-indigo-600 hover:underline">Login</Link>
      </p>
    </div>
  );
}
