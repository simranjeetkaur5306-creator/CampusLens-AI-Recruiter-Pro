import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { errorMessage } from "../../services/api";
import { ENDPOINTS } from "../../services/endpoints";

const input =
  "w-full rounded-lg border border-slate-300 px-3 py-2.5 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden";

export default function RegisterForm({ role }) {
  const isRecruiter = role === "recruiter";
  const navigate = useNavigate();
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", password: "", password2: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.first_name.trim() || !form.last_name.trim()) return setError("Please enter your first and last name.");
    if (!/^\S+@\S+\.\S+$/.test(form.email)) return setError("Please enter a valid email.");
    if (form.password.length < 8) return setError("Password must be at least 8 characters.");
    if (form.password !== form.password2) return setError("Passwords do not match.");

    const payload = {
      email: form.email.trim(),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      password: form.password,
      password2: form.password2,
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
        {isRecruiter
          ? "Post jobs and review AI-ranked candidates. You can add company details after logging in."
          : "Upload your resume and get matched to jobs."}
      </p>
      <form onSubmit={onSubmit} className="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="first_name" className="mb-1 block text-sm font-medium">First name</label>
            <input id="first_name" autoComplete="given-name" value={form.first_name} onChange={set("first_name")} className={input} />
          </div>
          <div>
            <label htmlFor="last_name" className="mb-1 block text-sm font-medium">Last name</label>
            <input id="last_name" autoComplete="family-name" value={form.last_name} onChange={set("last_name")} className={input} />
          </div>
        </div>
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium">Email</label>
          <input id="email" type="email" autoComplete="email" value={form.email} onChange={set("email")} className={input} />
        </div>
        <div>
          <label htmlFor="password" className="mb-1 block text-sm font-medium">Password</label>
          <input id="password" type="password" autoComplete="new-password" value={form.password} onChange={set("password")} className={input} />
          <p className="mt-1 text-xs text-slate-500">At least 8 characters. Avoid common or all-numeric passwords.</p>
        </div>
        <div>
          <label htmlFor="password2" className="mb-1 block text-sm font-medium">Confirm password</label>
          <input id="password2" type="password" autoComplete="new-password" value={form.password2} onChange={set("password2")} className={input} />
        </div>
        <button disabled={busy} className="w-full rounded-lg bg-navy-900 py-2.5 font-semibold text-white hover:bg-navy-800 disabled:opacity-60">
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600">
        Already registered? <Link to="/login" className="text-brand-700 hover:underline">Login</Link>
      </p>
    </div>
  );
}