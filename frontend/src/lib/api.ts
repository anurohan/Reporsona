import type {
  ChatResponse,
  ChatTurn,
  Conversation,
  ConversationDetail,
  Coverage,
  EthicalNotice,
  Insight,
  Job,
  KnowledgeGraph,
  PersonaCreateResponse,
  PersonaDetail,
  PersonaSummary,
  ProviderStatus,
  Resolution,
  SourceOut,
  SourceType,
  TimelineEvent,
  Topic,
  UploadResult,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
  "http://localhost:8000";

const API = `${API_BASE}/api`;

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
      cache: "no-store",
    });
  } catch (err) {
    throw new ApiError(
      "Could not reach the RePersona service. Check that the backend is running.",
      0
    );
  }

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail);
      }
    } catch {
      /* ignore body parse failure */
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function createPersona(input: {
  name: string;
  demo?: boolean;
}): Promise<PersonaCreateResponse> {
  return request<PersonaCreateResponse>("/personas/create", {
    method: "POST",
    body: JSON.stringify({ name: input.name, demo: input.demo ?? false }),
  });
}

export function listPersonas(): Promise<PersonaSummary[]> {
  return request<PersonaSummary[]>("/personas");
}

export function deletePersona(id: string): Promise<void> {
  return request<void>(`/personas/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export function getPersona(id: string): Promise<PersonaDetail> {
  return request<PersonaDetail>(`/personas/${encodeURIComponent(id)}`);
}

export function getSources(
  id: string,
  sourceType?: SourceType
): Promise<SourceOut[]> {
  const qs = sourceType
    ? `?source_type=${encodeURIComponent(sourceType)}`
    : "";
  return request<SourceOut[]>(
    `/personas/${encodeURIComponent(id)}/sources${qs}`
  );
}

export function getTopics(id: string): Promise<Topic[]> {
  return request<Topic[]>(`/personas/${encodeURIComponent(id)}/topics`);
}

export function getInsights(id: string): Promise<Insight[]> {
  return request<Insight[]>(`/personas/${encodeURIComponent(id)}/insights`);
}

export function getKnowledgeGraph(id: string): Promise<KnowledgeGraph> {
  return request<KnowledgeGraph>(
    `/personas/${encodeURIComponent(id)}/knowledge-graph`
  );
}

export function getJob(jobId: string): Promise<Job> {
  return request<Job>(`/jobs/${encodeURIComponent(jobId)}`);
}

export function sendChat(input: {
  persona_id: string;
  message: string;
  session_id?: string;
  history?: ChatTurn[];
  evidence_mode?: boolean;
  language?: string;
  mode?: string;
}): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({
      persona_id: input.persona_id,
      message: input.message,
      session_id: input.session_id ?? null,
      history: input.history ?? [],
      evidence_mode: input.evidence_mode ?? true,
      language: input.language ?? "en",
      mode: input.mode ?? "persona_simulation",
    }),
  });
}

export function getEthicalNotice(): Promise<EthicalNotice> {
  return request<EthicalNotice>("/ethical-notice");
}

export function getHealth(): Promise<Record<string, any>> {
  return request<Record<string, any>>("/health");
}

export function addTextSource(
  id: string,
  payload: {
    title?: string;
    text: string;
    source_type?: string;
    author?: string;
    url?: string;
    publication_date?: string;
  }
): Promise<UploadResult> {
  return request<UploadResult>(
    `/personas/${encodeURIComponent(id)}/sources/text`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

/**
 * Uploads a file as a new source. This intentionally bypasses the JSON
 * `request()` helper because it sends multipart FormData — the browser must
 * set the Content-Type header (with the multipart boundary) itself.
 */
export async function uploadSourceFile(
  id: string,
  file: File,
  title?: string
): Promise<UploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  if (title && title.trim()) formData.append("title", title.trim());

  let res: Response;
  try {
    res = await fetch(
      `${API_BASE}/api/personas/${encodeURIComponent(id)}/sources/upload`,
      {
        method: "POST",
        body: formData,
        cache: "no-store",
      }
    );
  } catch (err) {
    throw new ApiError(
      "Could not reach the RePersona service. Check that the backend is running.",
      0
    );
  }

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail);
      }
    } catch {
      /* ignore body parse failure */
    }
    throw new ApiError(detail, res.status);
  }

  return (await res.json()) as UploadResult;
}

// Convenience: the SSE endpoint URL for a job.
export function jobStreamUrl(jobId: string): string {
  return `${API}/jobs/${encodeURIComponent(jobId)}/stream`;
}

// ---- Provider status (§27) ------------------------------------------------ //
export function getProviders(): Promise<ProviderStatus[]> {
  return request<ProviderStatus[]>("/providers");
}

// ---- Identity resolution (§8) --------------------------------------------- //
export function resolveIdentity(input: {
  name: string;
  limit?: number;
}): Promise<Resolution> {
  return request<Resolution>("/personas/resolve", {
    method: "POST",
    body: JSON.stringify({ name: input.name, limit: input.limit ?? 5 }),
  });
}

// ---- Timeline (§12) ------------------------------------------------------- //
export function getTimeline(id: string): Promise<TimelineEvent[]> {
  return request<TimelineEvent[]>(
    `/personas/${encodeURIComponent(id)}/timeline`
  );
}

// ---- Knowledge coverage estimates (§21) ----------------------------------- //
export function getCoverage(id: string): Promise<Coverage> {
  return request<Coverage>(`/personas/${encodeURIComponent(id)}/coverage`);
}

// ---- Conversation memory (§20) -------------------------------------------- //
export function listConversations(personaId: string): Promise<Conversation[]> {
  return request<Conversation[]>(
    `/conversations?persona_id=${encodeURIComponent(personaId)}`
  );
}

export function getConversation(sessionId: string): Promise<ConversationDetail> {
  return request<ConversationDetail>(
    `/conversations/${encodeURIComponent(sessionId)}`
  );
}

export function renameConversation(
  sessionId: string,
  title: string
): Promise<Conversation> {
  return request<Conversation>(
    `/conversations/${encodeURIComponent(sessionId)}`,
    { method: "PATCH", body: JSON.stringify({ title }) }
  );
}

export function deleteConversation(sessionId: string): Promise<void> {
  return request<void>(`/conversations/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
}
