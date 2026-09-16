import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, Profile as ProfileData, getProfile } from "../api/client";
import NavBar from "../components/NavBar";

export default function Profile() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProfile()
      .then(setProfile)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load profile"));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <div className="mx-auto max-w-3xl px-6 py-8">
        <h1 className="mb-4 text-xl font-semibold text-gray-800">Your Profile</h1>
        {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {!profile && !error && <p className="text-sm text-gray-400">Loading…</p>}

        {profile && (
          <div className="space-y-6">
            <section className="rounded border border-gray-200 bg-white p-4">
              <h2 className="mb-2 text-sm font-semibold text-gray-700">
                Skills ({profile.skills.length})
              </h2>
              {profile.skills.length === 0 ? (
                <p className="text-sm text-gray-400">
                  No skills parsed yet —{" "}
                  <Link to="/onboarding" className="text-indigo-600 hover:underline">
                    upload or retry your resume in Settings
                  </Link>
                  .
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {profile.skills.map((skill, i) => (
                    <span
                      key={i}
                      title={skill.category}
                      className="rounded-full bg-indigo-50 px-3 py-1 text-xs text-indigo-700"
                    >
                      {skill.name}
                    </span>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded border border-gray-200 bg-white p-4">
              <h2 className="mb-2 text-sm font-semibold text-gray-700">Experience</h2>
              {profile.experience.length === 0 ? (
                <p className="text-sm text-gray-400">None parsed yet.</p>
              ) : (
                <div className="space-y-3">
                  {profile.experience.map((exp, i) => (
                    <div key={i}>
                      <p className="text-sm font-medium text-gray-800">
                        {exp.title} — {exp.company}{" "}
                        <span className="font-normal text-gray-400">({exp.dates})</span>
                      </p>
                      <ul className="ml-4 list-disc text-sm text-gray-600">
                        {exp.bullets.map((b, j) => (
                          <li key={j}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded border border-gray-200 bg-white p-4">
              <h2 className="mb-2 text-sm font-semibold text-gray-700">Projects</h2>
              {profile.projects.length === 0 ? (
                <p className="text-sm text-gray-400">None parsed yet.</p>
              ) : (
                <div className="space-y-2">
                  {profile.projects.map((p, i) => (
                    <div key={i}>
                      <p className="text-sm font-medium text-gray-800">{p.name}</p>
                      <p className="text-sm text-gray-600">{p.description}</p>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded border border-gray-200 bg-white p-4">
              <h2 className="mb-2 text-sm font-semibold text-gray-700">Education</h2>
              {profile.education.length === 0 ? (
                <p className="text-sm text-gray-400">None parsed yet.</p>
              ) : (
                <div className="space-y-1">
                  {profile.education.map((e, i) => (
                    <p key={i} className="text-sm text-gray-700">
                      {e.degree} — {e.school}{" "}
                      <span className="text-gray-400">({e.dates})</span>
                    </p>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
