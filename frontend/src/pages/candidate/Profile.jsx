import { useState } from "react";
import PageHeader from "../../components/ui/PageHeader";
import { EmptyState, ErrorState, Spinner } from "../../components/ui/States";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { getProfile, updateProfile } from "../../services/candidateApi";

const SKIP = new Set(["id", "user", "created_at", "updated_at", "password", "role", "email"]);

const labelFor = (key) => key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

function editableFields(profile) {
  return Object.entries(profile).filter(
    ([k, v]) => !SKIP.has(k) && (v === null || typeof v === "string" || typeof v === "number")
  );
}

export default function Profile() {
  const { user } = useAuth();
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(getProfile, []);
  const [edits, setEdits] = useState({});
  const [saving, setSaving] = useState(false);

  if (loading) return <Spinner label="Loading profile…" />;
  if (error || !data) return <ErrorState message={error} onRetry={reload} />;

  const fields = editableFields(data);
  const changed = Object.keys(edits).length > 0;

  const onSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {};
      for (const [k, v] of Object.entries(edits)) {
        payload[k] = typeof data[k] === "number" ? Number(v) : v;
      }
      await updateProfile(payload);
      toast.success("Profile updated.");
      setEdits({});
      reload();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <PageHeader title="My Profile" subtitle="Keep your details up to date." />
      <form onSubmit={onSave} className="max-w-2xl space-y-4 rounded-2xl border border-slate-200 bg-white p-6">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Account email</label>
          <input value={user?.email ?? ""} disabled className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-slate-500" />
        </div>

        {fields.length === 0 ? (
          <EmptyState title="No editable fields" text="The profile API did not return editable fields." />
        ) : (
          fields.map(([key, value]) => (
            <div key={key}>
              <label htmlFor={key} className="mb-1 block text-sm font-medium text-slate-700">{labelFor(key)}</label>
              <input
                id={key}
                value={edits[key] ?? value ?? ""}
                onChange={(e) => setEdits({ ...edits, [key]: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden"
              />
            </div>
          ))
        )}

        <button
          disabled={!changed || saving}
          className="rounded-lg bg-navy-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-800 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save changes"}
        </button>
      </form>
    </>
  );
}