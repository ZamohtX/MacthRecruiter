import { ChartFrame, DataTable } from "./ChartFrame";
import type { LegendItem } from "./ChartFrame";
import { AXIS_TICKS, CHANCE_LEVEL, formatDelta, formatScore, scalePercent } from "./scale";

/** Faixa à direita da pista, onde o rótulo de variação é escrito sem ser cortado. */
const GUTTER = "3rem";

export interface DumbbellDatum {
  label: string;
  before: number;
  after: number;
}

interface DumbbellProps {
  title: string;
  subtitle?: string;
  data: DumbbellDatum[];
  beforeLabel?: string;
  afterLabel?: string;
}

/**
 * Antes → depois por dimensão: a forma certa para a simulação pós-contratação.
 *
 * Uma cor, dois tons — o par de pontos é a mesma grandeza em dois momentos, não
 * duas séries independentes. O conector torna a direção e o tamanho da mudança
 * legíveis sem precisar comparar comprimentos de barra.
 */
export function Dumbbell({
  title,
  subtitle,
  data,
  beforeLabel = "Time hoje",
  afterLabel = "Time depois da contratação",
}: DumbbellProps) {
  const legend: LegendItem[] = [
    { label: beforeLabel, color: "var(--seq-track)" },
    { label: afterLabel, color: "var(--seq-fill)" },
  ];

  const table = (
    <DataTable
      headers={["Dimensão", beforeLabel, afterLabel, "Δ"]}
      rows={data.map((d) => [
        d.label,
        formatScore(d.before),
        formatScore(d.after),
        formatDelta(d.after - d.before),
      ])}
    />
  );

  // Rotula só os maiores movimentos: um número em cada ponto viraria ruído.
  const notable = new Set(
    [...data]
      .sort((a, b) => Math.abs(b.after - b.before) - Math.abs(a.after - a.before))
      .slice(0, 3)
      .map((d) => d.label),
  );

  return (
    <ChartFrame title={title} subtitle={subtitle} legend={legend} table={table}>
      <div className="space-y-1.5">
        {data.map((datum) => {
          const delta = datum.after - datum.before;
          const start = Math.min(datum.before, datum.after);
          const end = Math.max(datum.before, datum.after);

          return (
            <div key={datum.label} className="grid grid-cols-[minmax(9rem,14rem)_1fr] items-center gap-3">
              <span
                className="truncate text-xs"
                style={{ color: "var(--text-secondary)" }}
                title={datum.label}
              >
                {datum.label}
              </span>

              <div
                className="relative h-7"
                title={`${datum.label} — ${beforeLabel}: ${formatScore(datum.before)} · ${afterLabel}: ${formatScore(datum.after)} (${formatDelta(delta)})`}
                role="img"
                aria-label={`${datum.label}: de ${formatScore(datum.before)} para ${formatScore(datum.after)}, variação de ${formatDelta(delta)}`}
              >
                <div className="relative h-full" style={{ width: `calc(100% - ${GUTTER})` }}>
                <div aria-hidden className="pointer-events-none absolute inset-0">
                  {AXIS_TICKS.map((tick) => (
                    <span
                      key={tick}
                      className="absolute top-0 bottom-0 w-px"
                      style={{
                        left: `${scalePercent(tick)}%`,
                        background: tick === CHANCE_LEVEL ? "var(--baseline)" : "var(--gridline)",
                      }}
                    />
                  ))}
                </div>

                {/* Conector 2px entre os dois momentos. */}
                <div
                  className="absolute top-1/2 h-0.5 -translate-y-1/2 rounded-full"
                  style={{
                    left: `${scalePercent(start)}%`,
                    width: `${scalePercent(end) - scalePercent(start)}%`,
                    background: "var(--seq-track)",
                  }}
                />

                {/* Marcadores ≥8px com anel de 2px na cor da superfície, para
                    continuarem legíveis quando se sobrepõem. */}
                <span
                  className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
                  style={{
                    left: `${scalePercent(datum.before)}%`,
                    background: "var(--seq-track)",
                    boxShadow: "0 0 0 2px var(--surface-1)",
                  }}
                />
                <span
                  className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
                  style={{
                    left: `${scalePercent(datum.after)}%`,
                    background: "var(--seq-fill)",
                    boxShadow: "0 0 0 2px var(--surface-1)",
                  }}
                />

                {notable.has(datum.label) && Math.abs(delta) >= 0.01 && (
                  <span
                    className="tabular absolute top-1/2 -translate-y-1/2 pl-2 text-[11px] whitespace-nowrap"
                    style={{
                      left: `${scalePercent(end)}%`,
                      color: delta > 0 ? "var(--delta-up-good)" : "var(--diverge-neg)",
                    }}
                  >
                    {formatDelta(delta)}
                  </span>
                )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-[minmax(9rem,14rem)_1fr] gap-3">
        <span />
        <div className="relative mt-2 h-4" style={{ width: `calc(100% - ${GUTTER})` }} aria-hidden>
          {AXIS_TICKS.map((tick) => (
            <span
              key={tick}
              className="tabular absolute -translate-x-1/2 text-[10px]"
              style={{ left: `${scalePercent(tick)}%`, color: "var(--text-muted)" }}
            >
              {tick}
            </span>
          ))}
        </div>
      </div>

      <p className="mt-3 text-[11px]" style={{ color: "var(--text-muted)" }}>
        Média por dimensão depois da contratação:{" "}
        <span className="tabular">(média × N + nota do candidato) ÷ (N + 1)</span>. Dimensões que
        caem são esperadas — o candidato é mais fraco onde o time é forte.
      </p>
    </ChartFrame>
  );
}
