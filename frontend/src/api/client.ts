const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface CompileResult {
  status: "success" | "error";
  pdf_base64: string | null;
  log: string;
  message: string | null;
}

export interface Job {
  id: number;
  title: string;
  tex_source: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Request to ${path} failed: ${res.status} ${body}`);
  }
  return res.json() as Promise<T>;
}

export function createJob(title: string, texSource: string): Promise<Job> {
  return request<Job>("/jobs", {
    method: "POST",
    body: JSON.stringify({ title, tex_source: texSource }),
  });
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
