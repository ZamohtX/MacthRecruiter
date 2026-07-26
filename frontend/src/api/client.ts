import type {
  Application,
  ApplicationStatus,
  AssessmentAnswer,
  AssessmentProgress,
  CandidateSummary,
  ImpactAnalysis,
  Job,
  JobDetail,
  Questionnaire,
  SubmitAnswersResponse,
  Team,
  TeamDiagnosticStatus,
  TeamGapAnalysis,
  TeamInvite,
  TeamProfile,
  TokenResponse,
  User,
} from "./types";

// Vazio em dev: o proxy do Vite serve `/api` na mesma origem, então não há CORS.
const BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const API = `${BASE}/api/v1`;

const TOKEN_KEY = "matchrecruiter.token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

/** Erro de API com o status HTTP preservado, para a UI reagir a 401/403/404. */
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API}${path}`, { ...init, headers });

  if (!response.ok) {
    // O `detail` do FastAPI é string em erro de negócio e lista em erro de
    // validação (422); as duas formas viram uma mensagem legível.
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body?.detail)) {
        message = body.detail
          .map((d: { loc?: unknown[]; msg?: string }) => `${d.loc?.slice(1).join(".")}: ${d.msg}`)
          .join("; ");
      }
    } catch {
      // resposta sem corpo JSON — mantém o status como mensagem
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  auth: {
    google: (payload: { id_token: string; invite_token?: string | null; job_id?: string | null }) =>
      post<TokenResponse>("/auth/google", payload),
    me: () => request<User>("/auth/me"),
  },

  teams: {
    list: () => request<Team[]>("/teams"),
    create: (name: string) => post<Team>("/teams", { name }),
    invite: (teamId: string) => post<TeamInvite>(`/teams/${teamId}/invites`),
    profile: (teamId: string) => request<TeamProfile>(`/teams/${teamId}/soft-skills-profile`),
    diagnosticStatus: (teamId: string) =>
      request<TeamDiagnosticStatus>(`/teams/${teamId}/diagnostic-status`),
    gapAnalysis: (teamId: string) => request<TeamGapAnalysis>(`/teams/${teamId}/gap-analysis`),
  },

  questionnaires: {
    getDefault: () => request<Questionnaire>("/questionnaires/default"),
    get: (id: string) => request<Questionnaire>(`/questionnaires/${id}`),
    submit: (id: string, answers: { question_id: string; selected_option_id: string }[]) =>
      post<SubmitAnswersResponse>(`/questionnaires/${id}/answers`, { answers }),
    progress: (id: string) => request<AssessmentProgress>(`/questionnaires/${id}/my-progress`),
    myAnswers: (id: string) => request<AssessmentAnswer[]>(`/questionnaires/${id}/my-answers`),
  },

  jobs: {
    list: () => request<Job[]>("/jobs"),
    create: (payload: { title: string; description?: string | null; team_id: string }) =>
      post<Job>("/jobs", payload),
    get: (jobId: string) => request<JobDetail>(`/jobs/${jobId}`),
    questionnaire: (jobId: string) => request<Questionnaire>(`/jobs/${jobId}/questionnaire`),
    apply: (jobId: string) => post<{ message: string; application_id: string }>(`/jobs/${jobId}/apply`),
    submitAnswers: (jobId: string, answers: { question_id: string; selected_option_id: string }[]) =>
      post<SubmitAnswersResponse>(`/jobs/${jobId}/answers`, { answers }),
    myProgress: (jobId: string) => request<AssessmentProgress>(`/jobs/${jobId}/my-progress`),
    candidates: (jobId: string, params?: { min_fit_score?: number; status?: ApplicationStatus }) => {
      const search = new URLSearchParams();
      if (params?.min_fit_score !== undefined) search.set("min_fit_score", String(params.min_fit_score));
      if (params?.status) search.set("status", params.status);
      const query = search.toString();
      return request<CandidateSummary[]>(`/jobs/${jobId}/candidates${query ? `?${query}` : ""}`);
    },
    impact: (jobId: string, candidateId: string) =>
      post<ImpactAnalysis>(`/jobs/${jobId}/candidates/${candidateId}/impact-analysis`),
    updateStatus: (jobId: string, candidateId: string, status: ApplicationStatus) =>
      request<Application>(`/jobs/${jobId}/candidates/${candidateId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    hire: (jobId: string, candidateId: string) =>
      post<Application>(`/jobs/${jobId}/candidates/${candidateId}/hire`),
  },
};
