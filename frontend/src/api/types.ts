/**
 * Espelho tipado dos schemas Pydantic do backend.
 *
 * Manter estes tipos alinhados com `backend/app/schemas/` é o que faz o
 * TypeScript acusar quebra de contrato em tempo de build em vez de `undefined`
 * aparecer numa tela em produção.
 */

export type UserRole = "RECRUITER" | "MEMBER" | "CANDIDATE";

export type ApplicationStatus =
  | "APPLIED"
  | "SOFT_SKILLS_COMPLETED"
  | "UNDER_REVIEW"
  | "REJECTED"
  | "HIRED";

/** Posição de uma dimensão dentro do perfil do time — relativa, não absoluta. */
export type DimensionStatus = "GAP" | "ADEQUATE" | "STRENGTH";

export type FitVerdict =
  | "COMPLEMENTARY"
  | "BALANCED"
  | "EXCESSIVE_SUPPLEMENTARY"
  | "BELOW_MINIMUM"
  | "INSUFFICIENT_TEAM_DATA";

/** O que o candidato faz com a dimensão ao entrar no time. */
export type Contribution =
  | "FILLS_GAP"
  | "PARTIAL_LIFT"
  | "REDUNDANT"
  | "AGGRAVATES_GAP"
  | "DILUTES_STRENGTH"
  | "NEUTRAL";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  google_id: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Team {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}

export interface TeamInvite {
  invite_token: string;
  invite_url: string;
  expires_at: string | null;
}

/** Notas por chave (dimensão ou fator), sempre na escala 1–5. */
export type ScoreMap = Record<string, number>;

export interface TeamProfile {
  team_id: string;
  team_name: string;
  member_count: number;
  /** Camada observável: as 10 soft skills. É o que alimenta lacuna e fit. */
  dimension_scores: ScoreMap;
  /** Camada latente: os cinco fatores Big Five de onde as competências derivam. */
  trait_scores: ScoreMap;
  respondent_count: number;
  completion_rate: number;
  dispersion: number;
  low_confidence: boolean;
  confidence_note: string | null;
}

export interface TeamMemberStatus {
  user_id: string;
  name: string;
  email: string;
  joined_at: string;
  is_owner: boolean;
  assessment_completed: boolean;
  answered_questions: number;
  total_questions: number;
}

export interface TeamDiagnosticStatus {
  team_id: string;
  team_name: string;
  questionnaire_id: string | null;
  member_count: number;
  respondent_count: number;
  completion_rate: number;
  ready_for_job_opening: boolean;
  members: TeamMemberStatus[];
}

export interface DimensionGap {
  dimension: string;
  team_score: number;
  status: DimensionStatus;
  deficit: number;
  /** Peso da dimensão no perfil-alvo da vaga. Os pesos somam 1.0. */
  weight: number;
  members_below_threshold: number;
  members_assessed: number;
  rationale: string;
}

export interface TeamGapAnalysis {
  team_id: string;
  team_name: string;
  member_count: number;
  respondent_count: number;
  low_confidence: boolean;
  dimensions: DimensionGap[];
  priority_dimensions: string[];
  strengths: string[];
  target_profile: ScoreMap;
  summary: string;
}

export interface QuestionOption {
  id: string;
  text: string;
  position: number;
}

export interface Question {
  id: string;
  context: string;
  text: string;
  position: number;
  /** Bloco a que o cenário pertence. Só de apresentação. */
  level: number;
  options: QuestionOption[];
}

/**
 * Um bloco de cenários.
 *
 * Os rótulos vêm do backend de propósito: se o banco de itens crescer, a trilha
 * acompanha sozinha em vez de a interface inventar nome e contagem.
 */
export interface Level {
  index: number;
  title: string;
  subtitle: string;
  first_position: number;
  question_count: number;
  estimated_seconds: number;
}

export interface LevelProgress extends Level {
  answered_questions: number;
  is_complete: boolean;
}

export interface Questionnaire {
  id: string;
  title: string;
  description: string | null;
  is_default: boolean;
  format: string;
  traits: string[];
  derived_dimensions: string[];
  levels: Level[];
  estimated_minutes: number;
  questions: Question[];
}

export interface AssessmentProgress {
  questionnaire_id: string;
  user_id: string;
  total_questions: number;
  answered_questions: number;
  is_complete: boolean;
  missing_question_ids: string[];
  trait_scores: ScoreMap;
  dimension_scores: ScoreMap;
  levels: LevelProgress[];
  current_level: number;
  /** Soma dos tempos medidos. Nulo quando nenhuma resposta trouxe medida. */
  elapsed_seconds: number | null;
  estimated_seconds_remaining: number;
}

/** Uma escolha a enviar. `elapsed_ms` é o tempo gasto naquele cenário. */
export interface AnswerSubmission {
  question_id: string;
  selected_option_id: string;
  elapsed_ms?: number;
}

export interface SubmitAnswersResponse {
  message: string;
  questionnaire_id: string;
  saved_answers: number;
  progress: AssessmentProgress;
}

export interface AssessmentAnswer {
  id: string;
  question_id: string;
  selected_option_id: string;
  elapsed_ms: number | null;
  created_at: string;
}

export interface Job {
  id: string;
  team_id: string;
  questionnaire_id: string;
  title: string;
  description: string | null;
  created_at: string;
}

export interface JobDetail extends Job {
  team_name: string;
  questionnaire_title: string;
  application_count: number;
  team_assessment_ready: boolean;
}

export interface PostHiringSimulation {
  current_team_size: number;
  new_team_size: number;
  current_team_scores: ScoreMap;
  simulated_team_scores: ScoreMap;
  score_deltas: ScoreMap;
  gaps_filled: string[];
  gaps_missed: string[];
  overlaps: string[];
}

export interface DimensionInsight {
  dimension: string;
  team_score: number;
  candidate_score: number;
  simulated_score: number;
  delta: number;
  status: DimensionStatus;
  contribution: Contribution;
  explanation: string;
}

export interface ImpactAnalysis {
  job_id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_scores: ScoreMap;
  current_team_scores: ScoreMap;
  simulation: PostHiringSimulation;
  /** Alias de `complementary_fit_score`; é o critério de ranqueamento. */
  fit_score: number;
  complementary_fit_score: number;
  /** Semelhança com o time. Alto + fit baixo = mais do mesmo. */
  supplementary_fit_index: number;
  gap_coverage: number | null;
  balance_gain: number | null;
  redundancy: number | null;
  verdict: FitVerdict;
  risk_flags: string[];
  insights: DimensionInsight[];
}

export interface CandidateSummary {
  application_id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  status: ApplicationStatus;
  applied_at: string;
  soft_skills_completed: boolean;
  candidate_scores: ScoreMap | null;
  fit_score: number | null;
  supplementary_fit_index: number | null;
  verdict: FitVerdict | null;
  gaps_filled: string[];
}

export interface Application {
  id: string;
  job_id: string;
  candidate_id: string;
  status: ApplicationStatus;
  applied_at: string;
}

// ---------------------------------------------------------------------------
// Integração OxeTech Academy — geração de time a partir do pool de talentos.
// Espelha app/schemas/integration.py.
// ---------------------------------------------------------------------------

export interface SimulatedCandidate {
  candidate_id: string;
  /** Ausente quando a turma é reconstruída do banco (reabrir a aba). */
  aluno_id?: number | null;
  name: string;
  techs: string[];
  candidate_scores: ScoreMap;
  fit_score: number;
  supplementary_fit_index: number;
  verdict: FitVerdict;
  gaps_filled: string[];
  gaps_missed: string[];
}

export interface SimulateTeamResponse {
  /** "academy_api" quando veio da API real; "synthetic" quando a turma está sem alunos. */
  source: "academy_api" | "synthetic";
  team_id: string;
  team_name: string;
  team_scores: ScoreMap;
  job_id: string;
  job_title: string;
  respondent_count: number;
  dispersion_before: number;
  candidates: SimulatedCandidate[];
}

export interface AiSummaryResponse {
  summary: string;
  /** "ai" = veio do Gemini; "fallback" = texto-regra (Gemini indisponível). */
  source: "ai" | "fallback";
  model?: string | null;
}

export interface SimulateTeamRequest {
  team_size?: number;
  team_name?: string;
  job_title?: string;
  seed?: number;
  limit?: number;
  /** Força um time novo em vez de reaproveitar a turma já gerada. */
  regenerate?: boolean;
}
