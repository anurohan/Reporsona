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
  AuthResponse,
  UserOut,
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
        ...(typeof window !== "undefined" && localStorage.getItem("repersona_access_token")
          ? { Authorization: `Bearer ${localStorage.getItem("repersona_access_token")}` }
          : {}),
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
    if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/")) {
      window.location.assign(`/auth?next=${encodeURIComponent(window.location.pathname)}`);
    }
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

export function register(input: { email: string; password: string; display_name?: string }): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify(input) });
}

export function login(input: { email: string; password: string }): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(input) });
}

export function getCurrentUser(): Promise<UserOut> {
  return request<UserOut>("/auth/me");
}

export function logout(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" });
}

export function saveAuth(response: AuthResponse): void {
  if (typeof window !== "undefined") localStorage.setItem("repersona_access_token", response.access_token);
}

export function clearAuth(): void {
  if (typeof window !== "undefined") localStorage.removeItem("repersona_access_token");
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
        headers: typeof window !== "undefined" && localStorage.getItem("repersona_access_token")
          ? { Authorization: `Bearer ${localStorage.getItem("repersona_access_token")}` }
          : {},
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
  const token = typeof window !== "undefined" ? localStorage.getItem("repersona_access_token") : null;
  return `${API}/jobs/${encodeURIComponent(jobId)}/stream${token ? `?access_token=${encodeURIComponent(token)}` : ""}`;
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

// ---- Virtual Friends ------------------------------------------------------- //
import type {
  VirtualFriendSummary,
  TranscriptUploadResult,
  VFChatResponse,
  VFConversation,
  VFMemory,
  VFTranscript,
  ImportPreview,
  ImportConfirmation,
} from "./types";

export function listVirtualFriends(): Promise<VirtualFriendSummary[]> {
  return request<VirtualFriendSummary[]>("/virtual-friends/");
}

export function createVirtualFriend(input: {
  name: string;
  description?: string;
  avatar_color?: string;
}): Promise<VirtualFriendSummary> {
  return request<VirtualFriendSummary>("/virtual-friends/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getVirtualFriend(id: string): Promise<VirtualFriendSummary> {
  return request<VirtualFriendSummary>(
    `/virtual-friends/${encodeURIComponent(id)}`
  );
}

export function deleteVirtualFriend(id: string): Promise<void> {
  return request<void>(`/virtual-friends/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

// Transcripts
export async function uploadTranscript(
  friendId: string,
  file: File,
  targetSpeaker?: string
): Promise<TranscriptUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  if (targetSpeaker && targetSpeaker.trim()) {
    formData.append("target_speaker", targetSpeaker.trim());
  }

  let res: Response;
  try {
    res = await fetch(
      `${API_BASE}/api/virtual-friends/${encodeURIComponent(friendId)}/transcripts/upload`,
      {
        method: "POST",
        body: formData,
        headers: typeof window !== "undefined" && localStorage.getItem("repersona_access_token")
          ? { Authorization: `Bearer ${localStorage.getItem("repersona_access_token")}` }
          : {},
        cache: "no-store",
      }
    );
  } catch (err) {
    throw new ApiError(
      "Could not reach the service. Check that the backend is running.",
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
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }

  return (await res.json()) as TranscriptUploadResult;
}

export function addTextTranscript(
  friendId: string,
  payload: { text: string; title?: string; target_speaker?: string }
): Promise<TranscriptUploadResult> {
  return request<TranscriptUploadResult>(
    `/virtual-friends/${encodeURIComponent(friendId)}/transcripts/text`,
    { method: "POST", body: JSON.stringify(payload) }
  );
}

export function listTranscripts(friendId: string): Promise<VFTranscript[]> {
  return request<VFTranscript[]>(
    `/virtual-friends/${encodeURIComponent(friendId)}/transcripts`
  );
}

export function deleteTranscript(
  friendId: string,
  transcriptId: string
): Promise<void> {
  return request<void>(
    `/virtual-friends/${encodeURIComponent(friendId)}/transcripts/${encodeURIComponent(transcriptId)}`,
    { method: "DELETE" }
  );
}

export function reprocessTranscript(
  friendId: string,
  transcriptId: string
): Promise<TranscriptUploadResult> {
  return request<TranscriptUploadResult>(
    `/virtual-friends/${encodeURIComponent(friendId)}/transcripts/${encodeURIComponent(transcriptId)}/reprocess`,
    { method: "POST" }
  );
}

export function selectSpeaker(
  friendId: string,
  transcriptId: string,
  targetSpeaker: string
): Promise<any> {
  return request<any>(
    `/virtual-friends/${encodeURIComponent(friendId)}/transcripts/${encodeURIComponent(transcriptId)}/select-speaker`,
    { method: "POST", body: JSON.stringify({ target_speaker: targetSpeaker }) }
  );
}

// Chat
export function sendVFChat(input: {
  friend_id: string;
  message: string;
  session_id?: string;
  history?: ChatTurn[];
  language?: string;
}): Promise<VFChatResponse> {
  return request<VFChatResponse>(
    `/virtual-friends/${encodeURIComponent(input.friend_id)}/chat`,
    {
      method: "POST",
      body: JSON.stringify({
        friend_id: input.friend_id,
        message: input.message,
        session_id: input.session_id ?? null,
        history: input.history ?? [],
        language: input.language ?? "en",
      }),
    }
  );
}

export function listVFConversations(
  friendId: string
): Promise<VFConversation[]> {
  return request<VFConversation[]>(
    `/virtual-friends/${encodeURIComponent(friendId)}/conversations`
  );
}

export function deleteVFConversation(
  friendId: string,
  sessionId: string
): Promise<void> {
  return request<void>(
    `/virtual-friends/${encodeURIComponent(friendId)}/conversations/${encodeURIComponent(sessionId)}`,
    { method: "DELETE" }
  );
}

// Memory
export function listVFMemories(friendId: string): Promise<VFMemory[]> {
  return request<VFMemory[]>(
    `/virtual-friends/${encodeURIComponent(friendId)}/memories`
  );
}

export function deleteVFMemory(
  friendId: string,
  memoryId: string
): Promise<void> {
  return request<void>(
    `/virtual-friends/${encodeURIComponent(friendId)}/memories/${encodeURIComponent(memoryId)}`,
    { method: "DELETE" }
  );
}

export function uploadConversationPreview(
  file: File,
  platform: string,
  onProgress?: (progress: number) => void
): Promise<ImportPreview> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/virtual-friends/imports/preview`);
    const token = typeof window !== "undefined" ? localStorage.getItem("repersona_access_token") : null;
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onerror = () => reject(new ApiError("Could not reach the service.", 0));
    xhr.onload = () => {
      let body: any = {};
      try { body = JSON.parse(xhr.responseText); } catch { /* handled below */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as ImportPreview);
      else reject(new ApiError(body.detail || `${xhr.status} ${xhr.statusText}`, xhr.status));
    };
    const form = new FormData();
    form.append("file", file);
    form.append("platform", platform);
    xhr.send(form);
  });
}

export function confirmConversationImport(input: {
  import_id: string;
  target_speaker: string;
  friend_id?: string;
  friend_name?: string;
  description?: string;
}): Promise<ImportConfirmation> {
  return request<ImportConfirmation>(`/virtual-friends/imports/${encodeURIComponent(input.import_id)}/confirm`, {
    method: "POST",
    body: JSON.stringify({ target_speaker: input.target_speaker, friend_id: input.friend_id ?? null, friend_name: input.friend_name ?? null, description: input.description ?? "" }),
  });
}

export function deleteConversationImport(importId: string): Promise<void> {
  return request<void>(`/virtual-friends/imports/${encodeURIComponent(importId)}`, { method: "DELETE" });
}
