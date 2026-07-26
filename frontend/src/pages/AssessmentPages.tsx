import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router";

import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Callout, Card, ErrorState, PageTitle, Spinner } from "../components/ui";
import { AssessmentRunner } from "./AssessmentRunner";
import type { AssessmentSource } from "./AssessmentRunner";

/** Teste do time — instrumento padrão, respondido antes de qualquer vaga. */
export function MyAssessmentPage() {
  const questionnaire = useQuery({
    queryKey: ["questionnaire", "default"],
    queryFn: api.questionnaires.getDefault,
  });

  if (questionnaire.isPending) return <Spinner />;
  if (questionnaire.isError) return <ErrorState error={questionnaire.error} onRetry={() => questionnaire.refetch()} />;

  const id = questionnaire.data.id;

  const source: AssessmentSource = {
    key: ["assessment", "questionnaire", id],
    loadQuestionnaire: () => api.questionnaires.get(id),
    loadProgress: () => api.questionnaires.progress(id),
    loadAnswers: () => api.questionnaires.myAnswers(id),
    submit: (answers) => api.questionnaires.submit(id, answers),
  };

  return (
    <AssessmentRunner
      source={source}
      title="Diagnóstico comportamental"
      intro={
        <>
          {questionnaire.data.questions.length} situações de trabalho. Em cada uma, escolha a conduta
          mais parecida com a sua — <strong>todas são posturas profissionais legítimas</strong>, não
          existe alternativa certa.
        </>
      }
      onComplete={
        <Callout tone="good" title="Sua resposta entrou no diagnóstico do time">
          O perfil do time é a média das pessoas. Quanto mais integrantes responderem, menor a
          margem de erro do perfil-alvo da vaga.
        </Callout>
      }
    />
  );
}

/** Entrada por link de convite: vincula ao time e leva ao teste. */
export function InvitePage() {
  const { inviteToken = "" } = useParams();
  const { user, loading } = useAuth();

  if (loading) return <Spinner />;
  if (!user) return <Navigate to={`/login?convite=${inviteToken}&next=/meu-teste`} replace />;
  return <Navigate to="/meu-teste" replace />;
}

/** Página pública da vaga: candidatura + teste, na mesma tela. */
export function ApplyPage() {
  const { jobId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const { user, loading } = useAuth();

  const job = useQuery({ queryKey: ["job", jobId, "public"], queryFn: () => api.jobs.get(jobId), enabled: !!user });

  const apply = useMutation({ mutationFn: () => api.jobs.apply(jobId) });

  // Candidatar-se é idempotente no backend, então disparar na entrada é seguro
  // e evita um clique a mais entre a pessoa e o teste.
  useEffect(() => {
    if (user && job.isSuccess && apply.isIdle) apply.mutate();
  }, [user, job.isSuccess, apply]);

  if (loading) return <Spinner />;
  if (!user) return <Navigate to={`/login?vaga=${jobId}&next=/vaga/${jobId}`} replace />;

  if (job.isPending) return <Spinner />;
  if (job.isError) return <ErrorState error={job.error} onRetry={() => job.refetch()} />;

  const source: AssessmentSource = {
    key: ["assessment", "job", jobId],
    loadQuestionnaire: () => api.jobs.questionnaire(jobId),
    loadProgress: () => api.jobs.myProgress(jobId),
    // A vaga não expõe as respostas do candidato num endpoint próprio; as do
    // instrumento servem, porque é o mesmo teste.
    loadAnswers: () => api.questionnaires.myAnswers(job.data.questionnaire_id),
    submit: (answers) => api.jobs.submitAnswers(jobId, answers),
  };

  return (
    <div className="space-y-6">
      <PageTitle title={job.data.title} subtitle={`Processo seletivo · ${job.data.team_name}`} />

      {searchParams.get("erro") && <ErrorState error={new Error(searchParams.get("erro")!)} />}

      <Callout tone="info" title="Como este processo funciona">
        A equipe já respondeu este mesmo teste. Suas respostas são comparadas com o perfil do time
        para entender <strong>o que você acrescenta</strong> — não para ver se você se parece com
        eles. Leva cerca de 10 minutos e o progresso fica salvo.
      </Callout>

      <AssessmentRunner
        source={source}
        title="Teste comportamental"
        intro="Escolha, em cada situação, a conduta mais parecida com a sua."
        onComplete={
          <Callout tone="good" title="Candidatura completa">
            Seu perfil foi registrado e já entra na análise do recrutador. Você pode fechar esta
            página.
          </Callout>
        }
      />
    </div>
  );
}

/** Rota inicial de quem não é recrutador — evita cair numa lista de times vazia. */
export function CandidateHome() {
  return (
    <Card>
      <h2 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
        Bem-vindo
      </h2>
      <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
        Se você faz parte de um time, responda o diagnóstico comportamental. Se está se candidatando
        a uma vaga, use o link que recebeu.
      </p>
      <Link to="/meu-teste">
        <Button className="mt-4">Responder o diagnóstico</Button>
      </Link>
    </Card>
  );
}
