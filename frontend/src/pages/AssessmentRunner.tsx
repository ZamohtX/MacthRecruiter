import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";

import type { AssessmentProgress, Questionnaire, SubmitAnswersResponse } from "../api/types";
import { Button, Callout, Card, ErrorState, ProgressBar, Spinner } from "../components/ui";
import { ProfileBars } from "../viz/BarChart";

export interface AssessmentSource {
  /** Chave de cache — distingue o teste do time do teste de uma vaga. */
  key: string[];
  loadQuestionnaire: () => Promise<Questionnaire>;
  loadProgress: () => Promise<AssessmentProgress>;
  loadAnswers: () => Promise<{ question_id: string; selected_option_id: string }[]>;
  submit: (answers: { question_id: string; selected_option_id: string }[]) => Promise<SubmitAnswersResponse>;
}

interface AssessmentRunnerProps {
  source: AssessmentSource;
  title: string;
  intro: ReactNode;
  onComplete?: ReactNode;
}

export function AssessmentRunner({ source, title, intro, onComplete }: AssessmentRunnerProps) {
  const queryClient = useQueryClient();
  const [index, setIndex] = useState(0);
  const [reviewing, setReviewing] = useState(false);

  const questionnaire = useQuery({
    queryKey: [...source.key, "questionnaire"],
    queryFn: source.loadQuestionnaire,
  });

  const progress = useQuery({
    queryKey: [...source.key, "progress"],
    queryFn: source.loadProgress,
    enabled: questionnaire.isSuccess,
  });

  // Respostas já enviadas permitem retomar o teste de onde parou — sem isso,
  // fechar a aba no cenário 15 significaria recomeçar.
  const answers = useQuery({
    queryKey: [...source.key, "answers"],
    queryFn: source.loadAnswers,
    enabled: questionnaire.isSuccess,
  });

  const selection = useMemo(() => {
    const map = new Map<string, string>();
    for (const answer of answers.data ?? []) map.set(answer.question_id, answer.selected_option_id);
    return map;
  }, [answers.data]);

  const submit = useMutation({
    mutationFn: source.submit,
    onSuccess: (response) => {
      queryClient.setQueryData([...source.key, "progress"], response.progress);
      void queryClient.invalidateQueries({ queryKey: [...source.key, "answers"] });
    },
  });

  if (questionnaire.isPending) return <Spinner label="Carregando o teste…" />;
  if (questionnaire.isError) return <ErrorState error={questionnaire.error} onRetry={() => questionnaire.refetch()} />;

  const questions = questionnaire.data.questions;
  const answeredCount = selection.size;
  const isComplete = progress.data?.is_complete ?? false;

  function choose(questionId: string, optionId: string) {
    submit.mutate([{ question_id: questionId, selected_option_id: optionId }], {
      onSuccess: () => {
        // Avança sozinho só quando ainda há cenário à frente; no último, a
        // pessoa decide quando encerrar.
        if (index < questions.length - 1) setIndex((current) => current + 1);
      },
    });
  }

  // ---------------------------------------------------------------- resultado
  if (isComplete && !reviewing) {
    const traits = Object.entries(progress.data?.trait_scores ?? {})
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);
    const dimensions = Object.entries(progress.data?.dimension_scores ?? {})
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);

    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
            Teste concluído
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
            Você respondeu os {questions.length} cenários. Este é o seu perfil.
          </p>
        </div>

        {onComplete}

        <ProfileBars
          title="Seus fatores (Big Five)"
          subtitle="A camada que o teste mede diretamente."
          data={traits}
        />

        <ProfileBars
          title="Suas competências"
          subtitle="Derivadas dos fatores acima — não medidas separadamente."
          data={dimensions}
          color="var(--series-2)"
        />

        <Button variant="secondary" onClick={() => { setReviewing(true); setIndex(0); }}>
          Revisar minhas respostas
        </Button>
      </div>
    );
  }

  // ------------------------------------------------------------------- runner
  const question = questions[index];
  const selected = selection.get(question.id);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
          {title}
        </h1>
        <div className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          {intro}
        </div>
      </div>

      <ProgressBar value={answeredCount} max={questions.length} label="Cenários respondidos" />

      <Card>
        <p className="text-xs font-medium tracking-wide uppercase" style={{ color: "var(--text-muted)" }}>
          {index + 1} de {questions.length} · {question.context}
        </p>
        <p className="mt-3 text-base leading-relaxed" style={{ color: "var(--text-primary)" }}>
          {question.text}
        </p>

        <fieldset className="mt-5">
          <legend className="mb-3 text-sm" style={{ color: "var(--text-secondary)" }}>
            Qual conduta mais se parece com a sua? Não há resposta certa — todas são posturas
            profissionais legítimas.
          </legend>

          <div className="space-y-2">
            {question.options.map((option) => {
              const isSelected = selected === option.id;
              return (
                <label
                  key={option.id}
                  className="flex cursor-pointer items-start gap-3 rounded-lg p-3 text-sm transition-colors hover:bg-black/[0.03] dark:hover:bg-white/[0.06]"
                  style={{
                    border: `1px solid ${isSelected ? "var(--seq-fill)" : "var(--hairline)"}`,
                    background: isSelected ? "color-mix(in srgb, var(--seq-fill) 8%, transparent)" : undefined,
                  }}
                >
                  <input
                    type="radio"
                    name={question.id}
                    value={option.id}
                    checked={isSelected}
                    onChange={() => choose(question.id, option.id)}
                    disabled={submit.isPending}
                    className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--seq-fill)]"
                  />
                  <span style={{ color: "var(--text-primary)" }}>{option.text}</span>
                </label>
              );
            })}
          </div>
        </fieldset>

        {submit.isError && (
          <p className="mt-4 text-sm" style={{ color: "var(--status-critical)" }}>
            Não foi possível salvar: {submit.error instanceof Error ? submit.error.message : "erro"}
          </p>
        )}
      </Card>

      <div className="flex items-center justify-between">
        <Button variant="secondary" onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0}>
          ← Anterior
        </Button>

        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {submit.isPending ? "Salvando…" : "Respostas salvas automaticamente"}
        </span>

        {index < questions.length - 1 ? (
          <Button variant="secondary" onClick={() => setIndex((i) => Math.min(questions.length - 1, i + 1))}>
            Próximo →
          </Button>
        ) : (
          <Button onClick={() => setReviewing(false)} disabled={!isComplete}>
            {isComplete ? "Ver meu perfil" : `Faltam ${questions.length - answeredCount}`}
          </Button>
        )}
      </div>

      {!isComplete && answeredCount > 0 && answeredCount < questions.length && (
        <Callout tone="info" title="Você pode responder em etapas">
          O progresso fica salvo. Feche a aba e volte quando quiser: o teste continua de onde parou.
        </Callout>
      )}
    </div>
  );
}
