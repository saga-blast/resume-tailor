import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ApiError,
  Profile as ProfileData,
  addProfileProject,
  addProfileSkill,
  deleteProfileProject,
  deleteProfileSkill,
  getProfile,
} from "../api/client";
import NavBar from "../components/NavBar";

export default function Profile() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [skillName, setSkillName] = useState("");
  const [skillCategory, setSkillCategory] = useState("");
  const [addingSkill, setAddingSkill] = useState(false);

  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [addingProject, setAddingProject] = useState(false);

  useEffect(() => {
    load();
  }, []);

  function load() {
    getProfile()
      .then(setProfile)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load profile"));
  }

  async function handleAddSkill(e: FormEvent) {
    e.preventDefault();
    if (!skillName.trim()) return;
    setAddingSkill(true);
    setError(null);
    try {
      const skill = await addProfileSkill(skillName.trim(), skillCategory.trim() || "skill");
      setProfile((prev) => (prev ? { ...prev, skills: [...prev.skills, skill] } : prev));
      setSkillName("");
      setSkillCategory("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add skill");
    } finally {
      setAddingSkill(false);
    }
  }

  async function handleDeleteSkill(id: number) {
    try {
      await deleteProfileSkill(id);
      setProfile((prev) => (prev ? { ...prev, skills: prev.skills.filter((s) => s.id !== id) } : prev));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete skill");
    }
  }

  async function handleAddProject(e: FormEvent) {
    e.preventDefault();
    if (!projectName.trim()) return;
    setAddingProject(true);
    setError(null);
    try {
      const result = await addProfileProject(projectName.trim(), projectDescription.trim());
      setProfile((prev) => (prev ? { ...prev, projects: result.projects } : prev));
      setProjectName("");
      setProjectDescription("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add project");
    } finally {
      setAddingProject(false);
    }
  }

  async function handleDeleteProject(index: number) {
    try {
      const result = await deleteProfileProject(index);
      setProfile((prev) => (prev ? { ...prev, projects: result.projects } : prev));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete project");
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <div className="mx-auto max-w-3xl px-6 py-8">
        <h1 className="mb-1 text-xl font-semibold text-gray-800">Your Profile</h1>
        <p className="mb-4 text-sm text-gray-500">
          Skills and projects you add here are used the next time you run matching on any job.
        </p>
        {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {!profile && !error && <p className="text-sm text-gray-400">Loading…</p>}

        {profile && (
          <div className="space-y-6">
            <section className="rounded border border-gray-200 bg-white p-4">
              <h2 className="mb-2 text-sm font-semibold text-gray-700">
                Skills ({profile.skills.length})
              </h2>
              {profile.skills.length === 0 ? (
                <p className="mb-3 text-sm text-gray-400">
                  No skills parsed yet —{" "}
                  <Link to="/onboarding" className="text-indigo-600 hover:underline">
                    upload or retry your resume in Settings
                  </Link>
                  .
                </p>
              ) : (
                <div className="mb-3 flex flex-wrap gap-2">
                  {profile.skills.map((skill) => (
                    <span
                      key={skill.id}
                      title={skill.category}
                      className="flex items-center gap-1 rounded-full bg-indigo-50 px-3 py-1 text-xs text-indigo-700"
                    >
                      {skill.name}
                      <button
                        onClick={() => handleDeleteSkill(skill.id)}
                        className="text-indigo-400 hover:text-indigo-700"
                        aria-label={`Remove ${skill.name}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
              <form onSubmit={handleAddSkill} className="flex gap-2">
                <input
                  value={skillName}
                  onChange={(e) => setSkillName(e.target.value)}
                  placeholder="Skill name (e.g. RabbitMQ)"
                  className="flex-1 rounded border border-gray-300 px-3 py-1.5 text-sm"
                />
                <input
                  value={skillCategory}
                  onChange={(e) => setSkillCategory(e.target.value)}
                  placeholder="Category (optional)"
                  className="w-40 rounded border border-gray-300 px-3 py-1.5 text-sm"
                />
                <button
                  type="submit"
                  disabled={addingSkill || !skillName.trim()}
                  className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  Add
                </button>
              </form>
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
                <p className="mb-3 text-sm text-gray-400">None yet.</p>
              ) : (
                <div className="mb-3 space-y-2">
                  {profile.projects.map((p, i) => (
                    <div key={i} className="flex items-start justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-800">{p.name}</p>
                        <p className="text-sm text-gray-600">{p.description}</p>
                      </div>
                      <button
                        onClick={() => handleDeleteProject(i)}
                        className="shrink-0 text-xs text-gray-400 hover:text-red-600"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <form onSubmit={handleAddProject} className="space-y-2">
                <input
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="Project name"
                  className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
                />
                <div className="flex gap-2">
                  <input
                    value={projectDescription}
                    onChange={(e) => setProjectDescription(e.target.value)}
                    placeholder="Short description"
                    className="flex-1 rounded border border-gray-300 px-3 py-1.5 text-sm"
                  />
                  <button
                    type="submit"
                    disabled={addingProject || !projectName.trim()}
                    className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    Add
                  </button>
                </div>
              </form>
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
