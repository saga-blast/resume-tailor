const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface CompileResult {
  status: "success" | "error";
  pdf_base64: string | null;
  log: string;
  message: string | null;
}

export interface Requirement {
  text: string;
  category: string;
  years_required: string | null;
  priority: "must_have" | "nice_to_have";
}

export interface Job {
  id: number;
  title: string;
  company: string | null;
  tex_source: string;
  jd_raw_text: string | null;
  extracted_requirements: Requirement[] | null;
  match_percentage: number | null;
  status: string;
}

export interface OnboardingStatus {
  has_llm_config: boolean;
  has_template: boolean;
  has_profile: boolean;
}

export interface ProfileSkill {
  name: string;
  category: string;
  source: string;
}

export interface ProfileExperience {
  title: string;
  company: string;
  dates: string;
  bullets: string[];
}

export interface ProfileProject {
  name: string;
  description: string;
}

export interface ProfileEducation {
  school: string;
  degree: string;
  dates: string;
}

export interface Profile {
  skills: ProfileSkill[];
  experience: ProfileExperience[];
  projects: ProfileProject[];
  education: ProfileEducation[];
}

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = "";
    try {
      const data = await res.json();
      detail = data.detail ?? JSON.stringify(data);
    } catch {
      detail = await res.text().catch(() => "");
    }
    throw new ApiError(detail || `Request to ${path} failed: ${res.status}`, res.status);
  }
  return res.json() as Promise<T>;
}

export { ApiError };

// --- Auth ---

export function login(email: string, password: string): Promise<{ id: number; email: string }> {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getMe(): Promise<{ id: number; email: string }> {
  return request("/auth/me");
}

export function logout(): Promise<{ status: string }> {
  return request("/auth/logout", { method: "POST" });
}

// --- Onboarding ---

export function getOnboardingStatus(): Promise<OnboardingStatus> {
  return request("/onboarding/status");
}

export function saveLlmConfig(provider: string, model: string, apiKey: string): Promise<{ status: string }> {
  return request("/onboarding/llm-config", {
    method: "POST",
    body: JSON.stringify({ provider, model, api_key: apiKey }),
  });
}

export function getAvailableModels(): Promise<{ models: string[] }> {
  return request("/onboarding/available-models");
}

export function updateModel(model: string): Promise<{ status: string }> {
  return request("/onboarding/llm-config/model", {
    method: "PATCH",
    body: JSON.stringify({ model }),
  });
}

export function verifyModel(model: string): Promise<{ status: string }> {
  return request("/onboarding/verify-model", {
    method: "POST",
    body: JSON.stringify({ model }),
  });
}

export function uploadTemplate(file: File): Promise<{ status: string; profile: Profile }> {
  const formData = new FormData();
  formData.append("file", file);
  return request("/onboarding/template", {
    method: "POST",
    body: formData,
  });
}

// --- Profile ---

export function getProfile(): Promise<Profile> {
  return request("/profile");
}

// --- Jobs ---

export function createJob(params: {
  title: string;
  company?: string;
  texSource?: string;
  jdText?: string;
}): Promise<Job> {
  return request<Job>("/jobs", {
    method: "POST",
    body: JSON.stringify({
      title: params.title,
      company: params.company ?? null,
      tex_source: params.texSource ?? "",
      jd_text: params.jdText ?? null,
    }),
  });
}

export function listJobs(): Promise<Job[]> {
  return request<Job[]>("/jobs");
}

export function getJob(jobId: number): Promise<Job> {
  return request<Job>(`/jobs/${jobId}`);
}

export function getResume(jobId: number): Promise<{ tex_source: string }> {
  return request<{ tex_source: string }>(`/jobs/${jobId}/resume`);
}

export function saveResume(jobId: number, texSource: string): Promise<{ status: string }> {
  return request(`/jobs/${jobId}/resume`, {
    method: "PUT",
    body: JSON.stringify({ tex_source: texSource }),
  });
}

export function compileResume(jobId: number, texSource: string): Promise<CompileResult> {
  return request<CompileResult>(`/jobs/${jobId}/compile`, {
    method: "POST",
    body: JSON.stringify({ tex_source: texSource }),
  });
}
