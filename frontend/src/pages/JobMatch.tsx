import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ApiError,
  GenerateResumeResult,
  MatchSummary,
  answerMatchQuestion,
  generateResume,
  getMatches,
  runMatch,
} from "../api/client";
import NavBar from "../components/NavBar";

const CATEGORY_LABELS: Record<string, string> = {
  skill: "Skill",
  tool: "Tool",
  experience: "Experience",
  responsibility: "Responsibility",
};

export default function JobMatch() {
  const { jobId } = useParams<{ jobId: string }>();
  const id = Number(jobId);
  const navigate = useNavigate();

  const [summary, setSummary] = useState<MatchSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [matching, setMatching] = useState(false);
  const [answeringId, setAnsweringId] = useState<number | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateResult, setGenerateResult] = useState<GenerateResumeResult | null>(null);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await getMatches(id);
      setSummary(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load matches");
    } finally {
      setLoading(false);
    }
  }

  async function handleRunMatch() {
    setMatching(true);
    setError(null);
    try {
      const result = await runMatch(id);
      setSummary(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Matching failed");
    } finally {
      setMatching(false);
    }
  }

  async function handleAnswer(matchId: number, confirmed: boolean) {
    setAnsweringId(matchId);
    setError(null);
    try {
      const updated = await answerMatchQuestion(id, matchId, confirmed);
      setSummary((prev) => {
        if (!prev) return prev;
        const matches = prev.matches.map((m) => (m.id === matchId ? updated : m));
        const total = matches.length;
        const matchedCount = matches.filter((m) => m.match_status === "matched").length;
        return { match_percentage: total ? Math.round((matchedCount / total) * 1000) / 10 : 0, matches };
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save answer");
    } finally {
      setAnsweringId(null);
    }
  }

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    setGenerateResult(null);
    try {
      const result = await generateResume(id);
      setGenerateResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Resume generation failed");
    } finally {
      setGenerating(false);
    }
  }

  const matches = summary?.matches ?? [];
  const needsClarification = matches.filter((m) => m.match_status === "needs_clarification");
  const matched = matches.filter((m) => m.match_status === "matched");
  const declined = matches.filter((m) => m.match_status === "declined");
  const unmatched = matches.filter((m) => m.match_status === "unmatched");

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <div className="mx-auto max-w-3xl px-6 py-8">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <Link to={`/jobs/${id}`} className="text-sm text-gray-500 hover:text-gray-800">
              ← Back to job
            </Link>
            <h1 className="mt-1 text-xl font-semibold text-gray-800">Match & Clarify</h1>
          </div>
          {summary && (
            <div className="text-right">
              <div className="text-2xl font-semibold text-indigo-600">{summary.match_percentage}%</div>
              <div className="text-xs text-gray-400">match</div>
            </div>
          )}
        </div>

        {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {loading && <p className="text-sm text-gray-400">Loading…</p>}

        {!loading && matches.length === 0 && (
          <div className="rounded border border-gray-200 bg-white p-5">
            <p className="mb-3 text-sm text-gray-600">
              No matching run yet for this job. This compares the extracted requirements against your
              profile and previously confirmed/declined facts, and asks about any plausible gaps.
            </p>
            <button
              onClick={handleRunMatch}
              disabled={matching}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {matching ? "Matching (calls your LLM provider, ~10-20s)…" : "Run Matching"}
            </button>
          </div>
        )}

        {!loading && matches.length > 0 && (
          <div className="space-y-4">
            {needsClarification.length > 0 && (
              <section className="rounded border border-amber-200 bg-amber-50">
                <h2 className="border-b border-amber-200 px-4 py-2 text-sm font-semibold text-amber-800">
                  Needs your input ({needsClarification.length})
                </h2>
                <div className="divide-y divide-amber-100">
                  {needsClarification.map((m) => (
                    <div key={m.id} className="flex items-center justify-between px-4 py-3">
                      <div>
                        <p className="text-sm text-gray-800">{m.clarifying_question}</p>
                        <p className="text-xs text-gray-500">
                          {m.requirement_text} · {CATEGORY_LABELS[m.requirement_category] ?? m.requirement_category}
                        </p>
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <button
                          onClick={() => handleAnswer(m.id, true)}
                          disabled={answeringId === m.id}
                          className="rounded bg-emerald-600 px-3 py-1.5 text-sm text-white hover:bg-emerald-700 disabled:opacity-50"
                        >
                          Yes
                        </button>
                        <button
                          onClick={() => handleAnswer(m.id, false)}
                          disabled={answeringId === m.id}
                          className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-50"
                        >
                          No
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            <section className="rounded border border-gray-200 bg-white">
              <h2 className="border-b border-gray-100 px-4 py-2 text-sm font-semibold text-gray-700">
                Matched ({matched.length})
              </h2>
              <div className="divide-y divide-gray-100">
                {matched.map((m) => (
                  <div key={m.id} className="flex items-center justify-between px-4 py-2">
                    <span className="text-sm text-gray-800">{m.requirement_text}</span>
                    <span className="text-xs text-gray-500">{m.matched_skill_name}</span>
                  </div>
                ))}
              </div>
            </section>

            {declined.length > 0 && (
              <section className="rounded border border-gray-200 bg-white">
                <h2 className="border-b border-gray-100 px-4 py-2 text-sm font-semibold text-gray-700">
                  Declined ({declined.length})
                </h2>
                <div className="divide-y divide-gray-100">
                  {declined.map((m) => (
                    <div key={m.id} className="px-4 py-2 text-sm text-gray-500">
                      {m.requirement_text}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {unmatched.length > 0 && (
              <section className="rounded border border-gray-200 bg-white">
                <h2 className="border-b border-gray-100 px-4 py-2 text-sm font-semibold text-gray-700">
                  Not matched ({unmatched.length})
                </h2>
                <div className="divide-y divide-gray-100">
                  {unmatched.map((m) => (
                    <div key={m.id} className="px-4 py-2 text-sm text-gray-500">
                      {m.requirement_text}
                    </div>
                  ))}
                </div>
              </section>
            )}

            <div className="flex items-center justify-between">
              <button
                onClick={handleRunMatch}
                disabled={matching}
                className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
              >
                {matching ? "Re-matching…" : "Re-run Matching"}
              </button>
              <div className="text-right">
                {needsClarification.length > 0 && (
                  <p className="mb-1 text-xs text-amber-600">
                    {needsClarification.length} question{needsClarification.length === 1 ? "" : "s"} still
                    unanswered — you can generate now, but answering first gets more highlighted matches.
                  </p>
                )}
                <button
                  onClick={handleGenerate}
                  disabled={generating}
                  className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {generating
                    ? "Rewriting, highlighting, and fitting to one page (up to ~2 min)…"
                    : "Generate Resume"}
                </button>
              </div>
            </div>

            {generateResult && (
              <div
                className={`rounded border p-4 ${
                  generateResult.warning
                    ? "border-amber-200 bg-amber-50"
                    : "border-emerald-200 bg-emerald-50"
                }`}
              >
                <p
                  className={`mb-2 text-sm font-medium ${
                    generateResult.warning ? "text-amber-800" : "text-emerald-800"
                  }`}
                >
                  Resume generated
                  {generateResult.final_page_count !== null &&
                    ` — ${generateResult.final_page_count} page${generateResult.final_page_count === 1 ? "" : "s"}`}
                </p>
                <ul className="mb-3 space-y-0.5 text-xs text-emerald-700">
                  <li>
                    Rewrote {generateResult.bullets_rewritten} bullet
                    {generateResult.bullets_rewritten === 1 ? "" : "s"} to align with the JD.
                  </li>
                  {generateResult.bullets_trimmed > 0 && (
                    <li>
                      Trimmed {generateResult.bullets_trimmed} least-relevant bullet
                      {generateResult.bullets_trimmed === 1 ? "" : "s"} to fit one page.
                    </li>
                  )}
                  {generateResult.skills_added.length > 0 && (
                    <li>Added to resume: {generateResult.skills_added.join(", ")}</li>
                  )}
                  <li>
                    Highlighted {generateResult.keywords_highlighted.length} matched keyword
                    {generateResult.keywords_highlighted.length === 1 ? "" : "s"}.
                  </li>
                </ul>
                {generateResult.warning && (
                  <p className="mb-3 text-xs text-amber-700">{generateResult.warning}</p>
                )}
                <button
                  onClick={() => navigate(`/jobs/${id}/editor`)}
                  className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
                >
                  Open in Editor to Review & Compile
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
