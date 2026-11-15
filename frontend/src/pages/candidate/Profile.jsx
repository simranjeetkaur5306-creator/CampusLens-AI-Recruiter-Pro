import { useState } from "react";
import PageHeader from "../../components/ui/PageHeader";
import { ErrorState, Spinner } from "../../components/ui/States";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { getProfile, updateProfile } from "../../services/candidateApi";

const FIELDS = [
  ["phone", "Phone", "text"],
  ["headline", "Headline", "text"],
  ["location", "Location", "text"],
  ["university", "University", "text"],
  ["degree", "Degree", "text"],
  ["graduation_year", "Graduation year", "number"],
  ["linkedin_url", "LinkedIn URL", "url"],
  ["github_url", "GitHub URL", "url"],
  ["bio", "About you", "textarea"],
];

const input =
  "w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden";

export default function Profile() {
  const { user } = useAuth();
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(getProfile, []);
  const [edits, setEdits] = useState({});
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  if (loading) return <Spinner label="Loading profile…" />;
  if (error || !data) return <ErrorState message={error} onRetry={reload} />;

  const changed = Object.keys(edits).length > 0;
  const value = (key) => edits[key] ?? data[key] ?? "";

  const onSave = async (e) => {
    e.preventDefault();
    setFormError("");
    const payload = {};
    for (const [key, raw] of Object.entries(edits)) {
      const text = String(raw).trim();
      if (key === "graduation_year") {
        if (text === "") payload[key] = null;
        else {
          const year = Number(text);
          if (!Number.isInteger(year) || year < 1990 || year > 2100) return setFormError("Graduation year must be between 1990 and 2100.");
          payload[key] = year;
        }
      } else if (key.endsWith("_url") && text && !/^https?:\/\//i.test(text)) {
        return setFormError("Links must start with http:// or https://");
      } else if (key === "bio" && text.length > 1000) {
        return setFormError("About you can be at most 1000 characters.");
      } else {
        payload[key] = text;
      }
    }

    setSaving(true);
    try {
      await updateProfile(payload);
      toast.success("Profile updated.");
      setEdits({});
      await reload();
    } catch (err) {
      const msg = errorMessage(err);
      setFormError(msg);
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const fullName = [data.first_name ?? user?.first_name, data.last_name ?? user?.last_name].filter(Boolean).join(" ");

  return (
    <>
      <PageHeader title="My Profile" subtitle="Recruiters see these details when you apply." />
      <form onSubmit={onSave} className="max-w-2xl space-y-4 rounded-2xl border border-slate-200 bg-white p-6">
        {formError && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{formError}</p>}

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Account</label>
          <input
            value={[fullName, data.email ?? user?.email].filter(Boolean).join(" · ")}
            disabled
            className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-500"
          />
          <p className="mt-1 text-xs text-slate-500">Name and email are fixed after registration.</p>
        </div>

        {FIELDS.map(([key, label, type]) => (
          <div key={key}>
            <label htmlFor={key} className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
            {type === "textarea" ? (
              <textarea id={key} rows={4} maxLength={1000} value={value(key)} onChange={(e) => setEdits({ ...edits, [key]: e.target.value })} className={input} />
            ) : (
              <input
                id={key}
                type={type === "number" ? "number" : "text"}
                value={value(key)}
                onChange={(e) => setEdits({ ...edits, [key]: e.target.value })}
                className={input}
              />
            )}
          </div>
        ))}

        <button disabled={!changed || saving} className="rounded-lg bg-navy-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-800 disabled:opacity-50">
          {saving ? "Saving…" : "Save changes"}
        </button>
      </form>
    </>
  );
}