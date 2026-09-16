import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ApiError,
  Profile,
  getAvailableModels,
  getOnboardingStatus,
  getProfile,
  saveLlmConfig,
  updateModel,
  uploadTemplate,
  verifyModel,
} from "../api/client";

type Step = "loading" | "llm-config" | "pick-model" | "template" | "done";

const PROVIDER_DEFAULTS: Record<string, { label: string; model: string; keyHint: string; keyUrl: string }> = {
  anthropic: {
    label: "Anthropic (Claude)",
    model: "claude-sonnet-5",
    keyHint: "Requires API billing set up at console.anthropic.com",
    keyUrl: "console.anthropic.com",
  },
  groq: {
    label: "Groq (free tier, no card required)",
    model: "openai/gpt-oss-20b",
    keyHint: "Free API key from console.groq.com",
    keyUrl: "console.groq.com",
  },
};

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("loading");
  const [provider, setProvider] = useState<"anthropic" | "groq">("groq");
  const [model, setModel] = useState(PROVIDER_DEFAULTS.groq.model);
  const [apiKey, setApiKey] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [parsedProfile, setParsedProfile] = useState<Profile | null>(null);

  const [availableModels, setAvailableModels] = useState<string[] | null>(null);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [verifyError, setVerifyError] = useState<string | null>(null);

  useEffect(() => {
    getOnboardingStatus()
      .then((status) => {
        if (!status.has_llm_config) {
          setStep("llm-config");
        } else if (!status.has_profile) {
          setStep("template");
        } else {
          setStep("done");
          getProfile().then(setParsedProfile).catch(() => undefined);
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load status"));
  }, []);

  async function fetchModels() {
    setModelsLoading(true);
    setModelsError(null);
    setVerifyError(null);
    try {
      const result = await getAvailableModels();
      setAvailableModels(result.models);
      if (result.models.length > 0) setSelectedModel(result.models[0]);
    } catch (err) {
      setAvailableModels(null);
      setModelsError(
        err instanceof ApiError ? err.message : "Failed to fetch available models"
      );
    } finally {
      setModelsLoading(false);
    }
  }

  async function handleLlmConfigSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await saveLlmConfig(provider, model, apiKey);
      setApiKey("");
      setStep("pick-model");
      fetchModels();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save LLM config");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleConfirmModel(chosenModel: string) {
    if (!chosenModel) return;
    setSubmitting(true);
    setVerifyError(null);
    try {
      await verifyModel(chosenModel);
      await updateModel(chosenModel);
      setStep("template");
    } catch (err) {
      setVerifyError(
        err instanceof ApiError
          ? err.message
          : "Failed to verify this model — try a different one from the list."
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTemplateSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await uploadTemplate(file);
      setParsedProfile(result.profile);
      setStep("done");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to upload/parse template");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl px-6 py-10">
      <h1 className="mb-1 text-xl font-semibold text-gray-800">Set up Resume Tailor</h1>
      <p className="mb-6 text-sm text-gray-500">
        One-time setup: connect an LLM provider, then upload your resume.
      </p>

      {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {step === "loading" && <p className="text-sm text-gray-400">Loading…</p>}

      {step === "llm-config" && (
        <form onSubmit={handleLlmConfigSubmit} className="rounded border border-gray-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">Step 1 — Connect an LLM provider</h2>
          <label className="mb-1 block text-xs font-medium text-gray-600">Provider</label>
          <select
            value={provider}
            onChange={(e) => {
              const next = e.target.value as "anthropic" | "groq";
              setProvider(next);
              setModel(PROVIDER_DEFAULTS[next].model);
            }}
            className="mb-3 w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm"
          >
            <option value="groq">{PROVIDER_DEFAULTS.groq.label}</option>
            <option value="anthropic">{PROVIDER_DEFAULTS.anthropic.label}</option>
          </select>
          <label className="mb-1 block text-xs font-medium text-gray-600">Starting model (you'll confirm this next)</label>
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="mb-3 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <label className="mb-1 block text-xs font-medium text-gray-600">API key</label>
          <input
            type="password"
            required
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={provider === "groq" ? "gsk_..." : "sk-ant-..."}
            className="mb-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <p className="mb-4 text-xs text-gray-400">
            {PROVIDER_DEFAULTS[provider].keyHint} ({PROVIDER_DEFAULTS[provider].keyUrl}). Stored encrypted at
            rest on your own machine; never leaves the backend except to call the provider's API.
          </p>
          <button
            type="submit"
            disabled={submitting}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {submitting ? "Saving…" : "Continue"}
          </button>
        </form>
      )}

      {step === "pick-model" && (
        <div className="rounded border border-gray-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">
            Confirm which model to use
          </h2>
          <p className="mb-3 text-xs text-gray-500">
            Model lineups change over time, so instead of guessing, this asks your provider directly
            which models your key can actually use right now.
          </p>

          {modelsLoading && <p className="text-sm text-gray-400">Fetching available models…</p>}

          {!modelsLoading && modelsError && (
            <div className="mb-3">
              <p className="mb-2 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{modelsError}</p>
              <button
                onClick={fetchModels}
                className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
              >
                Retry
              </button>
              <p className="mt-3 mb-1 text-xs font-medium text-gray-600">
                Or type a model ID manually:
              </p>
              <div className="flex gap-2">
                <input
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
                  placeholder="e.g. llama-3.1-8b-instant"
                />
                <button
                  onClick={() => handleConfirmModel(selectedModel)}
                  disabled={submitting || !selectedModel}
                  className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {submitting ? "Verifying…" : "Use this"}
                </button>
              </div>
            </div>
          )}

          {!modelsLoading && availableModels && (
            <>
              {availableModels.length === 0 ? (
                <p className="text-sm text-gray-400">
                  Your key returned no available models. Double-check it's valid for this provider.
                </p>
              ) : (
                <>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    Available models ({availableModels.length})
                  </label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="mb-4 w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm"
                  >
                    {availableModels.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleConfirmModel(selectedModel)}
                    disabled={submitting}
                    className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {submitting ? "Verifying…" : "Confirm & Continue"}
                  </button>
                </>
              )}
            </>
          )}

          {verifyError && (
            <p className="mt-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{verifyError}</p>
          )}
        </div>
      )}

      {step === "template" && (
        <form onSubmit={handleTemplateSubmit} className="rounded border border-gray-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">Step 2 — Upload your resume</h2>
          <p className="mb-3 text-xs text-gray-500">
            Upload your existing LaTeX resume (.tex). Your LLM provider will read it and parse out your skills,
            experience, projects, and education.
          </p>
          <input
            type="file"
            accept=".tex,text/plain"
            required
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="mb-2 block w-full text-sm"
          />
          <button
            type="button"
            onClick={() => {
              setError(null);
              setStep("pick-model");
              fetchModels();
            }}
            className="mb-4 text-xs text-indigo-600 hover:underline"
          >
            Wrong model? Change it
          </button>
          <button
            type="submit"
            disabled={submitting || !file}
            className="block rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {submitting ? "Uploading and parsing (calls your LLM provider, may take ~10-20s)…" : "Upload & parse"}
          </button>
        </form>
      )}

      {step === "done" && (
        <div className="rounded border border-gray-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">All set</h2>
          {parsedProfile && (
            <div className="mb-4 space-y-2 text-sm text-gray-600">
              <p>
                Parsed <strong>{parsedProfile.skills.length}</strong> skills,{" "}
                <strong>{parsedProfile.experience.length}</strong> experience entries,{" "}
                <strong>{parsedProfile.projects.length}</strong> projects.
              </p>
            </div>
          )}
          <div className="flex gap-3">
            <button
              onClick={() => navigate("/jobs")}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Continue to Jobs
            </button>
            <button
              onClick={() => {
                setParsedProfile(null);
                setFile(null);
                setError(null);
                setStep("template");
              }}
              className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
            >
              Replace resume
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
