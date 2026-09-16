import { useEffect, useState } from "react";
import { ApiError, PreferenceEntry, deletePreference, listPreferences, updatePreference } from "../api/client";
import NavBar from "../components/NavBar";

export default function Preferences() {
  const [prefs, setPrefs] = useState<PreferenceEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      setPrefs(await listPreferences());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load preferences");
    }
  }

  async function handleToggle(pref: PreferenceEntry) {
    setBusyId(pref.id);
    try {
      const next = pref.status === "confirmed" ? "declined" : "confirmed";
      const updated = await updatePreference(pref.id, next);
      setPrefs((prev) => prev?.map((p) => (p.id === pref.id ? updated : p)) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update preference");
    } finally {
      setBusyId(null);
    }
  }

  async function handleForget(pref: PreferenceEntry) {
    setBusyId(pref.id);
    try {
      await deletePreference(pref.id);
      setPrefs((prev) => prev?.filter((p) => p.id !== pref.id) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete preference");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <div className="mx-auto max-w-3xl px-6 py-8">
        <h1 className="mb-1 text-xl font-semibold text-gray-800">Preferences</h1>
        <p className="mb-4 text-sm text-gray-500">
          Every fact you've confirmed or declined during job matching — this is what makes sure the same
          question is never asked twice. Flip a status or forget an entry entirely to have it asked again.
        </p>

        {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {!prefs && !error && <p className="text-sm text-gray-400">Loading…</p>}
        {prefs && prefs.length === 0 && (
          <p className="text-sm text-gray-400">
            Nothing here yet — answer a clarifying question during job matching and it'll show up here.
          </p>
        )}

        {prefs && prefs.length > 0 && (
          <div className="divide-y divide-gray-200 rounded border border-gray-200 bg-white">
            {prefs.map((p) => (
              <div key={p.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="text-sm text-gray-800">{p.fact_text}</p>
                  <p className="text-xs text-gray-500">
                    {p.question_text} → {p.answer_text}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-1 text-xs ${
                      p.status === "confirmed" ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {p.status}
                  </span>
                  <button
                    onClick={() => handleToggle(p)}
                    disabled={busyId === p.id}
                    className="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50 disabled:opacity-50"
                  >
                    Flip
                  </button>
                  <button
                    onClick={() => handleForget(p)}
                    disabled={busyId === p.id}
                    className="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50 disabled:opacity-50"
                  >
                    Forget
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
