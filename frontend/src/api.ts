// Mirrors the response models in backend/app/schemas.py.

export type DocumentInfo = {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
};

export type Source = {
  number: number;
  document_id: string;
  filename: string;
  page: number;
  text: string;
  score: number;
  cited: boolean;
};

export type Usage = {
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number | null;
};

export type ChatResponse = {
  answer: string;
  sources: Source[];
  usage: Usage | null;
};

export function listDocuments(): Promise<DocumentInfo[]> {
  return request("/documents");
}

export function uploadDocument(file: File): Promise<DocumentInfo> {
  const body = new FormData();
  body.append("file", file);
  return request("/documents", { method: "POST", body });
}

export function askQuestion(question: string, documentIds: string[]): Promise<ChatResponse> {
  return request("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, document_ids: documentIds }),
  });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(errorMessage(body) ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

// FastAPI returns {"detail": "..."} for our errors and a list for validation errors.
function errorMessage(body: unknown): string | null {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === "string") return detail[0].msg;
  return null;
}
