/**
 * Camada de jogo do teste situacional: trilha de níveis, sequência e checkpoint.
 *
 * **O que estas peças deliberadamente não fazem: dizer se a escolha foi boa.**
 * Todas as condutas de um cenário são profissionalmente defensáveis e as cargas
 * nos fatores nunca chegam ao navegador. Um "acertou!" exigiria uma alternativa
 * correta — que é justamente o que o formato SJT existe para não ter. Então o
 * reforço é sempre de **progresso e ritmo**: quanto falta, qual bloco fechou, há
 * quanto tempo a pessoa está respondendo.
 *
 * Isso não é uma versão pobre da mecânica. Num teste sem resposta certa, o que
 * prende é ver o fim se aproximar; um elogio genérico a cada tela seria ruído, e
 * um elogio específico seria a chave de correção vazando.
 */

import type { Level, LevelProgress } from "../api/types";

/** Duração em texto curto. Abaixo de um minuto, contar segundos é ansiedade. */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return "menos de 1 min";
  const minutes = Math.round(seconds / 60);
  return `${minutes} min`;
}

// ---------------------------------------------------------------- trilha
interface LevelTrackProps {
  levels: LevelProgress[];
  /** Uma posição por cenário, na ordem de exibição: respondido ou não. */
  answered: boolean[];
  currentIndex: number;
}

/**
 * Os níveis como blocos de pontos, com o cenário atual marcado.
 *
 * O estado de cada ponto nunca é só cor: o resumo em texto acima da trilha diz
 * o mesmo em palavras, o nível concluído ganha "✓" e cada ponto tem rótulo
 * acessível próprio.
 */
export function LevelTrack({ levels, answered, currentIndex }: LevelTrackProps) {
  const total = answered.length;
  const answeredCount = answered.filter(Boolean).length;
  const current = levels.find(
    (level) => currentIndex >= level.first_position && currentIndex < level.first_position + level.question_count,
  );

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-xs">
        <span style={{ color: "var(--text-secondary)" }}>
          {current ? (
            <>
              Nível {current.index + 1} de {levels.length} · <strong>{current.title}</strong>
            </>
          ) : (
            <>{levels.length} níveis</>
          )}
        </span>
        <span className="tabular" style={{ color: "var(--text-muted)" }}>
          {answeredCount} / {total} cenários
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        {levels.map((level) => {
          const slice = answered.slice(level.first_position, level.first_position + level.question_count);
          return (
            <div key={level.index} className="flex items-center gap-1.5" title={`${level.title} — ${level.subtitle}`}>
              {slice.map((isAnswered, offset) => {
                const position = level.first_position + offset;
                const isCurrent = position === currentIndex;
                return (
                  <span
                    key={position}
                    aria-label={`Cenário ${position + 1}: ${isAnswered ? "respondido" : "em aberto"}${
                      isCurrent ? ", é onde você está" : ""
                    }`}
                    role="img"
                    className="h-2.5 w-2.5 rounded-full transition-colors"
                    style={{
                      background: isAnswered ? "var(--seq-fill)" : "var(--seq-track)",
                      // O cenário atual ganha um anel, não outra cor: quem não
                      // distingue os dois azuis continua vendo onde está.
                      outline: isCurrent ? "2px solid var(--text-primary)" : undefined,
                      outlineOffset: "2px",
                    }}
                  />
                );
              })}
              <span
                aria-hidden
                className="ml-0.5 text-xs"
                style={{ color: level.is_complete ? "var(--status-good)" : "transparent" }}
              >
                ✓
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// -------------------------------------------------------------- sequência
/**
 * Cenários seguidos nesta sessão.
 *
 * Sequência de **ritmo**, não de acerto: conta quantos cenários novos a pessoa
 * respondeu sem sair da tela. Zera ao recarregar, e isso é honesto — não existe
 * mérito acumulado a preservar, existe embalo.
 */
export function StreakPill({ count }: { count: number }) {
  if (count < 2) return null;

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs"
      style={{ border: "1px solid var(--seq-fill)", color: "var(--text-primary)" }}
    >
      <span aria-hidden style={{ color: "var(--seq-fill)" }}>
        »
      </span>
      <span className="tabular">{count}</span> seguidos
    </span>
  );
}

// ------------------------------------------------------------- checkpoint
interface LevelCheckpointProps {
  completed: LevelProgress;
  next: Level | undefined;
  answeredCount: number;
  totalQuestions: number;
  elapsedSeconds: number | null;
  remainingSeconds: number;
  streak: number;
  onContinue: () => void;
}

/**
 * Tela entre um nível e o seguinte.
 *
 * A função não é comemorar: é criar um ponto de parada explícito. Quem cansa no
 * cenário 12 fecha a aba num limite marcado e volta — em vez de abandonar no
 * meio de um bloco e não retomar nunca.
 */
export function LevelCheckpoint({
  completed,
  next,
  answeredCount,
  totalQuestions,
  elapsedSeconds,
  remainingSeconds,
  streak,
  onContinue,
}: LevelCheckpointProps) {
  return (
    <div
      className="rounded-xl p-6 text-center"
      style={{ background: "var(--surface-1)", border: "1px solid var(--seq-fill)" }}
    >
      <p className="text-xs font-medium tracking-wide uppercase" style={{ color: "var(--text-muted)" }}>
        Nível {completed.index + 1} concluído
      </p>
      <h2 className="mt-1 text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
        {completed.title}
      </h2>

      <dl className="mx-auto mt-5 grid max-w-md grid-cols-3 gap-3 text-center">
        <div>
          <dt className="text-xs" style={{ color: "var(--text-secondary)" }}>
            Respondidos
          </dt>
          <dd className="mt-0.5 text-lg font-semibold tabular" style={{ color: "var(--text-primary)" }}>
            {answeredCount}/{totalQuestions}
          </dd>
        </div>
        <div>
          <dt className="text-xs" style={{ color: "var(--text-secondary)" }}>
            Tempo até aqui
          </dt>
          <dd className="mt-0.5 text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
            {elapsedSeconds === null ? "—" : formatDuration(elapsedSeconds)}
          </dd>
        </div>
        <div>
          <dt className="text-xs" style={{ color: "var(--text-secondary)" }}>
            Falta
          </dt>
          <dd className="mt-0.5 text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
            {remainingSeconds > 0 ? `~${formatDuration(remainingSeconds)}` : "nada"}
          </dd>
        </div>
      </dl>

      {streak >= 2 && (
        <p className="mt-4">
          <StreakPill count={streak} />
        </p>
      )}

      {next && (
        <div className="mt-6">
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            A seguir — <strong style={{ color: "var(--text-primary)" }}>{next.title}</strong>: {next.subtitle}
          </p>
          <button
            type="button"
            onClick={onContinue}
            className="mt-4 inline-flex items-center justify-center rounded-lg bg-[var(--seq-fill)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            Continuar
          </button>
          <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
            Pode parar aqui: o progresso está salvo e o teste retoma neste ponto.
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- resumo
/** Como foi a corrida — sem nota, porque não existe nota a dar. */
export function RunSummary({
  totalQuestions,
  levelCount,
  elapsedSeconds,
}: {
  totalQuestions: number;
  levelCount: number;
  elapsedSeconds: number | null;
}) {
  const items: { label: string; value: string }[] = [
    { label: "Cenários", value: String(totalQuestions) },
    { label: "Níveis", value: String(levelCount) },
    // Sem medida é diferente de zero: respostas enviadas por script não têm
    // tempo, e inventar "0 min" mentiria sobre a duração do instrumento.
    { label: "Tempo", value: elapsedSeconds === null ? "não medido" : formatDuration(elapsedSeconds) },
  ];

  return (
    <dl className="grid grid-cols-3 gap-3">
      {items.map((item) => (
        <div
          key={item.label}
          className="rounded-xl p-4"
          style={{ background: "var(--surface-1)", border: "1px solid var(--hairline)" }}
        >
          <dt className="text-xs" style={{ color: "var(--text-secondary)" }}>
            {item.label}
          </dt>
          <dd className="mt-1 text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
