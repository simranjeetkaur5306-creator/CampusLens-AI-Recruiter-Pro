import { useState } from "react";
import PageHeader from "../../components/ui/PageHeader";
import { EmptyState, ErrorState, Spinner } from "../../components/ui/States";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { getCompanyProfile, updateCompanyProfile } from "../../services/recruiterApi";

// Fields the API returns but does not accept for writing.
const READ_ONLY = new Set(["id", "email", "first_name", "last_name", "created_at", "updated_at"]);
const labelFor = (key) => key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
const input =
  "w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden";

export default function CompanyProfile() {
  const { user } = useAuth();
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(getCompanyProfile, []);
  const [edits, setEdits] = useState({});
  const [saving, setSaving] = useState(false);

  if (loading) return <Spinner label="Loading company profile…" />;
  if (error || !data) return <ErrorState message={error} onRetry={reload} />;

  const fields = Object.entries(data).filter(
    ([k, v]) => !READ_ONLY.has(k) && (v === null || typeof v === "string")
  );
  const changed = Object.keys(edits).length > 0;

  const onSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateCompanyProfile(edits);
      toast.success("Company profile updated.");
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
      <PageHeader
        title="Company Profile"
        subtitle="Your company name is used on new job postings when you leave the job's company field empty."
      />
      <form onSubmit={onSave} className="max-w-2xl space-y-4 rounded-2xl border border-slate-200 bg-white p-6">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Account</label>
          <input
            value={[user?.first_name, user?.last_name].filter(Boolean).join(" ") + (user?.email ? ` · ${user.email}` : "")}
            disabled
            className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-500"
          />
        </div>

        {fields.length === 0 ? (
          <EmptyState title="No editable fields" text="The profile API did not return editable fields." />
        ) : (
          fields.map(([key, value]) => (
            <div key={key}>
              <label htmlFor={key} className="mb-1 block text-sm font-medium text-slate-700">{labelFor(key)}</label>
              {key.includes("description") ? (
                <textarea id={key} rows={5} value={edits[key] ?? value ?? ""} onChange={(e) => setEdits({ ...edits, [key]: e.target.value })} className={input} />
              ) : (
                <input id={key} value={edits[key] ?? value ?? ""} onChange={(e) => setEdits({ ...edits, [key]: e.target.value })} className={input} />
              )}
            </div>
          ))
        )}

        <button disabled={!changed || saving} className="rounded-lg bg-navy-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-800 disabled:opacity-50">
          {saving ? "Saving…" : "Save changes"}
        </button>
      </form>
    </>
  );
}