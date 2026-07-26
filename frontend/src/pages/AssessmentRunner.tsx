import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import type {
  AnswerSubmission,
  AssessmentAnswer,
  AssessmentProgress,
  LevelProgress,
  Questionnaire,
  SubmitAnswersResponse,
} from "../api/types";
import { Button, Callout, Card, ErrorState, ProgressBar, Spinner } from "../components/ui";
import { LevelCheckpoint, LevelTrack, RunSummary, StreakPill, formatDuration } from "../components/game";
import { ProfileBars } from "../viz/BarChart";

export interface AssessmentSource {
  /** Chave de cache — distingue o teste do time do teste de uma vaga. */
  key: string[];
  loadQuestionnaire: () => Promise<Questionnaire>;
  loadProgress: () => Promise<AssessmentProgress>;
  loadAnswers: () => Promise<AssessmentAnswer[]>;
  submit: (answers: AnswerSubmission[]) => Promise<SubmitAnswersResponse>;
}

interface AssessmentRunnerProps {
  source: AssessmentSource;
  title: string;
  intro: ReactNode;
  onComplete?: ReactNode;
}

/**
 * Tempo que a confirmação fica na tela antes de avançar sozinho.
 *
 * Sem pausa nenhuma o cenário seguinte aparece antes de a pessoa registrar que
 * a escolha foi salva, e o teste vira um borrão. Perto de meio segundo é o
 * suficiente para ver a marca sem virar espera.
 */
const FEEDBACK_MS = 420;

/**
 * Acima disto a medida é descartada em vez de enviada.
 *
 * Aba aberta e esquecida não é tempo de leitura. Como estes números vão calibrar
 * a duração-alvo do instrumento (hoje uma premissa), um outlier de 40 minutos
 * estraga a estatística — e não temos como distinguir leitura lenta de almoço.
 */
const MAX_PLAUSIBLE_ANSWER_MS = 5 * 60 * 1000;

/**
 * Relógio monotônico, fora do corpo do componente.
 *
 * `performance.now()` é impuro e não pode ser chamado no caminho de render — o
 * lint acusa, com razão. Isolado aqui, só quem chama são o efeito e o
 * manipulador de evento. É `performance` e não `Date` porque acerto de relógio
 * do sistema no meio do teste produziria duração negativa.
 */
const monotonicNow = () => performance.now();

export function AssessmentRunner({ source, title, intro, onComplete }: AssessmentRunnerProps) {
  const queryClient = useQueryClient();
  const [index, setIndex] = useState(0);
  const [reviewing, setReviewing] = useState(false);
  // Nível recém-fechado, à espera do "Continuar". Null = respondendo.
  const [checkpoint, setCheckpoint] = useState<LevelProgress | null>(null);
  // Cenários novos respondidos sem sair da tela. Ritmo, não mérito: zera ao
  // recarregar, porque não há nada acumulado a preservar.
  const [streak, setStreak] = useState(0);
  const [justSaved, setJustSaved] = useState<string | null>(null);

  // Cronômetro do cenário na tela. Em ref, não em estado: mudar não deve
  // redesenhar nada.
  const shownAt = useRef<number>(0);
  const advanceTimer = useRef<number | null>(null);

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

  // Reinicia o cronômetro a cada cenário exibido. Só escrita em ref: a
  // confirmação some sozinha porque é comparada com o cenário na tela.
  const questionId = questionnaire.data?.questions[index]?.id;
  useEffect(() => {
    shownAt.current = monotonicNow();
  }, [questionId]);

  // Timer pendente não pode sobreviver à saída da tela: avançaria o índice de um
  // componente que não existe mais.
  useEffect(() => () => window.clearTimeout(advanceTimer.current ?? undefined), []);

  if (questionnaire.isPending) return <Spinner label="Carregando o teste…" />;
  if (questionnaire.isError) return <ErrorState error={questionnaire.error} onRetry={() => questionnaire.refetch()} />;

  const questions = questionnaire.data.questions;
  const answeredCount = selection.size;
  const isComplete = progress.data?.is_complete ?? false;
  const elapsedSeconds = progress.data?.elapsed_seconds ?? null;
  const remainingSeconds = progress.data?.estimated_seconds_remaining ?? 0;

  // Estado de cada cenário na ordem de exibição. A trilha e as contagens saem
  // todas daqui, então não há como a bolinha discordar do número ao lado.
  const answered = questions.map((question) => selection.has(question.id));
  const levels: LevelProgress[] = questionnaire.data.levels.map((level) => {
    const block = answered.slice(level.first_position, level.first_position + level.question_count);
    const count = block.filter(Boolean).length;
    return { ...level, answered_questions: count, is_complete: count === level.question_count };
  });

  function goTo(next: number) {
    window.clearTimeout(advanceTimer.current ?? undefined);
    setJustSaved(null);
    setIndex(Math.min(questions.length - 1, Math.max(0, next)));
  }

  function choose(questionId: string, optionId: string) {
    const isNewAnswer = !selection.has(questionId);
    const spent = Math.round(monotonicNow() - shownAt.current);

    submit.mutate(
      [
        {
          question_id: questionId,
          selected_option_id: optionId,
          elapsed_ms: spent <= MAX_PLAUSIBLE_ANSWER_MS ? spent : undefined,
        },
      ],
      {
        onSuccess: (response) => {
          setJustSaved(questionId);
          if (isNewAnswer && !reviewing) setStreak((current) => current + 1);

          const question = questions.find((q) => q.id === questionId);
          const closed = response.progress.levels[question?.level ?? 0];
          const hasNextLevel = (question?.level ?? 0) < response.progress.levels.length - 1;

          // Nível fechado → checkpoint. Revisão de resposta antiga não abre
          // checkpoint: a pessoa não acabou de vencer nada, está conferindo.
          if (closed?.is_complete && hasNextLevel && isNewAnswer && !reviewing) {
            advanceTimer.current = window.setTimeout(() => setCheckpoint(closed), FEEDBACK_MS);
            return;
          }

          // No último cenário quem decide encerrar é a pessoa.
          if (index < questions.length - 1) {
            advanceTimer.current = window.setTimeout(() => setIndex((current) => current + 1), FEEDBACK_MS);
          }
        },
      },
    );
  }

  // -------------------------------------------------------------- checkpoint
  if (checkpoint) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <LevelCheckpoint
          completed={checkpoint}
          next={questionnaire.data.levels[checkpoint.index + 1]}
          answeredCount={answeredCount}
          totalQuestions={questions.length}
          elapsedSeconds={elapsedSeconds}
          remainingSeconds={remainingSeconds}
          streak={streak}
          onContinue={() => {
            const next = questionnaire.data.levels[checkpoint.index + 1];
            setCheckpoint(null);
            // Retoma no primeiro cenário em aberto do bloco seguinte — quem
            // respondeu fora de ordem não recomeça no que já respondeu.
            const start = next?.first_position ?? index;
            const openInBlock = answered.findIndex((done, position) => !done && position >= start);
            goTo(openInBlock >= 0 ? openInBlock : start);
          }}
        />
      </div>
    );
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

        <RunSummary
          totalQuestions={questions.length}
          levelCount={questionnaire.data.levels.length}
          elapsedSeconds={elapsedSeconds}
        />

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
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
            {title}
          </h1>
          <div className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
            {intro}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StreakPill count={streak} />
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {remainingSeconds > 0 ? `~${formatDuration(remainingSeconds)} restantes` : "último trecho"}
          </span>
        </div>
      </div>

      <ProgressBar value={answeredCount} max={questions.length} label="Cenários respondidos" />
      <LevelTrack levels={levels} answered={answered} currentIndex={index} />

      <Card>
        <p className="text-xs font-medium tracking-wide uppercase" style={{ color: "var(--text-muted)" }}>
          {index + 1} de {questions.length} · {question.context}
        </p>
        <p className="mt-3 text-base leading-relaxed" style={{ color: "var(--text-primary)" }}>
          {question.text}
        </p>

        <fieldset className="mt-5" disabled={submit.isPending}>
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
                    className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--seq-fill)]"
                  />
                  <span style={{ color: "var(--text-primary)" }}>{option.text}</span>
                </label>
              );
            })}
          </div>
        </fieldset>

        {/* Confirmação de que a escolha entrou — nunca de que ela foi boa. Um
            "ótima resposta!" precisaria de uma alternativa correta, que este
            instrumento não tem de propósito. */}
        <p className="mt-4 text-sm" role="status" aria-live="polite" style={{ minHeight: "1.25rem" }}>
          {submit.isPending && <span style={{ color: "var(--text-muted)" }}>Salvando…</span>}
          {!submit.isPending && justSaved === question.id && (
            <span style={{ color: "var(--status-good)" }}>
              <span aria-hidden>✓</span> Escolha registrada
            </span>
          )}
        </p>

        {submit.isError && (
          <p className="text-sm" style={{ color: "var(--status-critical)" }}>
            Não foi possível salvar: {submit.error instanceof Error ? submit.error.message : "erro"}
          </p>
        )}
      </Card>

      <div className="flex items-center justify-between">
        <Button variant="secondary" onClick={() => goTo(index - 1)} disabled={index === 0}>
          ← Anterior
        </Button>

        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          Respostas salvas automaticamente
        </span>

        {index < questions.length - 1 ? (
          <Button variant="secondary" onClick={() => goTo(index + 1)}>
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
