import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, Job, deleteJob, listJobs } from "../api/client";
import NavBar from "../components/NavBar";

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  requirements_extracted: "Requirements extracted",
  extraction_failed: "Extraction failed",
  questions_pending: "Questions pending",
  matched: "Matched",
  generated: "Generated",
  compiled: "Compiled",
  downloaded: "Downloaded",
};

export default function JobsList() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    load();
  }, []);

  function load() {
    listJobs()
      .then(setJobs)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load jobs"));
  }

  async function handleDelete(e: React.MouseEvent, job: Job) {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`Delete "${job.title}"? This can't be undone.`)) return;
    setDeletingId(job.id);
    setError(null);
    try {
      await deleteJob(job.id);
      setJobs((prev) => prev?.filter((j) => j.id !== job.id) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete job");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <div className="mx-auto max-w-3xl px-6 py-8">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-800">Job Applications</h1>
          <Link
            to="/jobs/new"
            className="rounded bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            + New Job Application
          </Link>
        </div>

        {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {!jobs && !error && <p className="text-sm text-gray-400">Loading…</p>}

        {jobs && jobs.length === 0 && (
          <p className="text-sm text-gray-400">No job applications yet — create one to get started.</p>
        )}

        {jobs && jobs.length > 0 && (
          <div className="divide-y divide-gray-200 rounded border border-gray-200 bg-white">
            {jobs
              .slice()
              .reverse()
              .map((job) => (
                <div
                  key={job.id}
                  onClick={() => navigate(job.jd_raw_text ? `/jobs/${job.id}` : `/jobs/${job.id}/editor`)}
                  className="flex cursor-pointer items-center justify-between px-4 py-3 hover:bg-gray-50"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-800">{job.title}</p>
                    {job.company && <p className="text-xs text-gray-500">{job.company}</p>}
                  </div>
                  <div className="flex items-center gap-3">
                    {job.match_percentage !== null && (
                      <span className="text-xs text-gray-500">{Math.round(job.match_percentage)}% match</span>
                    )}
                    <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">
                      {STATUS_LABELS[job.status] ?? job.status}
                    </span>
                    <button
                      onClick={(e) => handleDelete(e, job)}
                      disabled={deletingId === job.id}
                      className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-500 hover:border-red-300 hover:text-red-600 disabled:opacity-50"
                    >
                      {deletingId === job.id ? "Deleting…" : "Delete"}
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
