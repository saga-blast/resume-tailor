import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, createJob } from "../api/client";
import NavBar from "../components/NavBar";

export default function NewJob() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [jdText, setJdText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const job = await createJob({
        title: title || "Untitled",
        company: company || undefined,
        jdText,
      });
      navigate(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create job");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <div className="mx-auto max-w-2xl px-6 py-8">
        <h1 className="mb-4 text-xl font-semibold text-gray-800">New Job Application</h1>
        {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <form onSubmit={handleSubmit} className="rounded border border-gray-200 bg-white p-5">
          <label className="mb-1 block text-xs font-medium text-gray-600">Title</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Senior Backend Engineer"
            className="mb-3 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <label className="mb-1 block text-xs font-medium text-gray-600">Company (optional)</label>
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            className="mb-3 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <label className="mb-1 block text-xs font-medium text-gray-600">Job description</label>
          <textarea
            required
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            rows={12}
            placeholder="Paste the job description here…"
            className="mb-4 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={submitting}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {submitting ? "Extracting requirements (calls your LLM provider, ~10-20s)…" : "Extract Requirements"}
          </button>
        </form>
      </div>
    </div>
  );
}
