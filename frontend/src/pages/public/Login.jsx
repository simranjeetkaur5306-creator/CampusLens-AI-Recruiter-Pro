import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { errorMessage } from "../../services/api";
import { homeFor } from "../../utils/routes";

const input =
  "w-full rounded-lg border border-slate-300 px-3 py-2.5 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-hidden";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.email || !form.password) return setError("Please enter your email and password.");
    setBusy(true);
    try {
      const me = await login(form.email.trim(), form.password);
      navigate(homeFor(me.role), { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-2xl font-bold tracking-tight">Welcome back</h1>
      <p className="mt-1 text-sm text-slate-500">Log in to your candidate or recruiter account.</p>
      {location.state?.registered && (
        <p className="mt-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">Account created. Please log in.</p>
      )}
      <form onSubmit={onSubmit} className="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <div>
          <label className="mb-1 block text-sm font-medium">Email</label>
          <input type="email" autoComplete="email" value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} className={input} />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Password</label>
          <input type="password" autoComplete="current-password" value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })} className={input} />
        </div>
        <button disabled={busy} className="w-full rounded-lg bg-indigo-600 py-2.5 font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
          {busy ? "Logging in…" : "Login"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600">
        New here? <Link to="/register/candidate" className="text-indigo-600 hover:underline">Candidate</Link> ·{" "}
        <Link to="/register/recruiter" className="text-indigo-600 hover:underline">Recruiter</Link>
      </p>
    </div>
  );
}
