import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, Job, Requirement, getJob } from "../api/client";
import NavBar from "../components/NavBar";

const CATEGORY_LABELS: Record<string, string> = {
  skill: "Skill",
  tool: "Tool",
  experience: "Experience",
  responsibility: "Responsibility",
};

function RequirementRow({ req }: { req: Requirement }) {
  return (
    <div className="flex items-center justify-between border-b border-gray-100 px-3 py-2 last:border-b-0">
      <div>
        <span className="text-sm text-gray-800">{req.text}</span>
        {req.years_required && (
          <span className="ml-2 text-xs text-gray-400">({req.years_required})</span>
        )}
      </div>
      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
        {CATEGORY_LABELS[req.category] ?? req.category}
      </span>
    </div>
  );
}

export default function JobDetail() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showJd, setShowJd] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    getJob(Number(jobId))
      .then(setJob)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load job"));
  }, [jobId]);

  const mustHaves = job?.extracted_requirements?.filter((r) => r.priority === "must_have") ?? [];
  const niceToHaves = job?.extracted_requirements?.filter((r) => r.priority === "nice_to_have") ?? [];

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <div className="mx-auto max-w-3xl px-6 py-8">
        {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {!job && !error && <p className="text-sm text-gray-400">Loading…</p>}

        {job && (
          <>
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h1 className="text-xl font-semibold text-gray-800">{job.title}</h1>
                {job.company && <p className="text-sm text-gray-500">{job.company}</p>}
              </div>
              <Link
                to={`/jobs/${job.id}/editor`}
                className="rounded border border-gray-300 px-3 py-2 text-sm hover:bg-gray-50"
              >
                Open Resume Editor
              </Link>
            </div>

            {job.status === "extraction_failed" && (
              <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">
                Requirement extraction failed for this job. Check your LLM configuration in Onboarding
                and try creating the job again.
              </p>
            )}

            <div className="mb-4 rounded border border-gray-200 bg-white">
              <button
                onClick={() => setShowJd((v) => !v)}
                className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-gray-700"
              >
                Job Description
                <span className="text-gray-400">{showJd ? "▲" : "▼"}</span>
              </button>
              {showJd && (
                <pre className="whitespace-pre-wrap border-t border-gray-100 px-4 py-3 text-sm text-gray-600">
                  {job.jd_raw_text}
                </pre>
              )}
            </div>

            {job.extracted_requirements && (
              <div className="space-y-4">
                <section className="rounded border border-gray-200 bg-white">
                  <h2 className="border-b border-gray-100 px-4 py-2 text-sm font-semibold text-gray-700">
                    Must-have ({mustHaves.length})
                  </h2>
                  {mustHaves.map((r, i) => (
                    <RequirementRow key={i} req={r} />
                  ))}
                </section>

                <section className="rounded border border-gray-200 bg-white">
                  <h2 className="border-b border-gray-100 px-4 py-2 text-sm font-semibold text-gray-700">
                    Nice-to-have ({niceToHaves.length})
                  </h2>
                  {niceToHaves.map((r, i) => (
                    <RequirementRow key={i} req={r} />
                  ))}
                </section>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
