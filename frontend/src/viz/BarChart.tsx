import type { ReactNode } from "react";

import type { DimensionStatus } from "../api/types";
import { ChartFrame, DataTable } from "./ChartFrame";
import type { LegendItem } from "./ChartFrame";
import {
  AXIS_TICKS,
  CHANCE_LEVEL,
  DIMENSION_STATUS_COLOR,
  DIMENSION_STATUS_ICON,
  DIMENSION_STATUS_LABEL,
  formatScore,
  scalePercent,
} from "./scale";

/**
 * Faixa reservada à direita da pista, onde o rótulo da ponta é escrito.
 *
 * Sem ela, o valor de uma barra em 5.00 sairia do cartão — e rótulo cortado é
 * pior que rótulo nenhum.
 */
const GUTTER = "3rem";

/**
 * Comprimento mínimo da barra.
 *
 * Uma nota no piso da escala (1.00) tem comprimento zero e sumiria, deixando um
 * número na tela sem marca que o represente. O toco diz "existe, e está no
 * mínimo".
 */
const MIN_BAR = "3px";

const ROW_GRID = "grid grid-cols-[minmax(9rem,14rem)_1fr] items-center gap-3";

/**
 * Pista do gráfico: ocupa a largura útil menos a faixa do rótulo.
 *
 * Grade, barras e marcadores vivem aqui dentro e são posicionados em
 * porcentagem da escala; rótulos podem transbordar para a faixa sem serem
 * cortados, porque nada aqui usa `overflow: hidden`.
 */
function Track({ height, children, title }: { height: string; children: ReactNode; title?: string }) {
  return (
    <div className={`relative ${height}`} title={title}>
      <div className="relative h-full" style={{ width: `calc(100% - ${GUTTER})` }}>
        <div aria-hidden className="pointer-events-none absolute inset-0">
          {AXIS_TICKS.map((tick) => (
            <span
              key={tick}
              className="absolute top-0 bottom-0 w-px"
              style={{
                left: `${scalePercent(tick)}%`,
                // Hairline sólida, um passo fora da superfície. Nunca tracejada.
                // O tique do acaso é um passo mais forte: é a referência de leitura.
                background: tick === CHANCE_LEVEL ? "var(--baseline)" : "var(--gridline)",
              }}
            />
          ))}
        </div>
        {children}
      </div>
    </div>
  );
}

function AxisRow() {
  return (
    <div className={ROW_GRID}>
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
  );
}

function ChanceCaption() {
  return (
    <p className="mt-3 text-[11px]" style={{ color: "var(--text-muted)" }}>
      Escala 1–5 ancorada no acaso: <strong>3.0</strong> é a frequência que uma resposta aleatória
      produziria. Nota alta significa “escolhe estas condutas bem mais que o acaso”, não “domina a
      competência”.
    </p>
  );
}

function RowLabel({ label, status }: { label: string; status?: DimensionStatus }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="truncate text-xs" style={{ color: "var(--text-secondary)" }} title={label}>
        {label}
      </span>
      {status && (
        // Ícone + texto acessível junto da cor: status nunca fica só na cor.
        <span
          className="shrink-0 text-[10px]"
          style={{ color: DIMENSION_STATUS_COLOR[status] }}
          title={DIMENSION_STATUS_LABEL[status]}
        >
          {DIMENSION_STATUS_ICON[status]}
          <span className="sr-only">{DIMENSION_STATUS_LABEL[status]}</span>
        </span>
      )}
    </div>
  );
}

export interface BarDatum {
  label: string;
  value: number;
  status?: DimensionStatus;
}

interface ProfileBarsProps {
  title: string;
  subtitle?: string;
  data: BarDatum[];
  /** Série única: uma cor para todas as barras. Nunca escurecer-onde-maior —
   *  isso duplicaria o comprimento da barra na cor sem acrescentar informação. */
  color?: string;
  emptyMessage?: string;
}

export function ProfileBars({
  title,
  subtitle,
  data,
  color = "var(--series-1)",
  emptyMessage = "Sem dados ainda.",
}: ProfileBarsProps) {
  const table = (
    <DataTable headers={["Dimensão", "Nota"]} rows={data.map((d) => [d.label, formatScore(d.value)])} />
  );

  if (data.length === 0) {
    return (
      <ChartFrame title={title} subtitle={subtitle} table={table}>
        <p className="py-8 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          {emptyMessage}
        </p>
      </ChartFrame>
    );
  }

  return (
    <ChartFrame title={title} subtitle={subtitle} table={table}>
      <div className="space-y-2">
        {data.map((datum) => (
          <div key={datum.label} className={ROW_GRID}>
            <RowLabel label={datum.label} status={datum.status} />
            <Track height="h-5">
              {/* Barra fina, ponta arredondada, quadrada na base. */}
              <div
                className="absolute top-1/2 left-0 h-3 -translate-y-1/2 rounded-r"
                style={{ width: `${scalePercent(datum.value)}%`, minWidth: MIN_BAR, background: color }}
                role="img"
                aria-label={`${datum.label}: ${formatScore(datum.value)} de 5`}
              />
              <span
                className="tabular absolute top-1/2 -translate-y-1/2 pl-1.5 text-[11px] whitespace-nowrap"
                style={{ left: `${scalePercent(datum.value)}%`, color: "var(--text-secondary)" }}
              >
                {datum.value.toFixed(2)}
              </span>
            </Track>
          </div>
        ))}
      </div>

      <AxisRow />
      <ChanceCaption />
    </ChartFrame>
  );
}

export interface ComparisonDatum {
  label: string;
  teamValue: number;
  candidateValue: number;
  status?: DimensionStatus;
}

interface ComparisonBarsProps {
  title: string;
  subtitle?: string;
  data: ComparisonDatum[];
  teamLabel?: string;
  candidateLabel?: string;
}

/**
 * Duas séries lado a lado: perfil do time × perfil do candidato.
 *
 * Sem rótulo em cada barra — vinte números na tela viram ruído e ninguém lê. O
 * valor vem do eixo, do hover e da tabela.
 */
export function ComparisonBars({
  title,
  subtitle,
  data,
  teamLabel = "Time hoje",
  candidateLabel = "Candidato",
}: ComparisonBarsProps) {
  const legend: LegendItem[] = [
    { label: teamLabel, color: "var(--series-1)" },
    { label: candidateLabel, color: "var(--series-2)" },
  ];

  const table = (
    <DataTable
      headers={["Dimensão", teamLabel, candidateLabel, "Diferença"]}
      rows={data.map((d) => [
        d.label,
        formatScore(d.teamValue),
        formatScore(d.candidateValue),
        formatScore(d.candidateValue - d.teamValue),
      ])}
    />
  );

  return (
    <ChartFrame title={title} subtitle={subtitle} legend={legend} table={table}>
      <div className="space-y-3">
        {data.map((datum) => (
          <div key={datum.label} className={ROW_GRID}>
            <RowLabel label={datum.label} status={datum.status} />
            <Track
              height="h-8"
              title={`${datum.label} — ${teamLabel}: ${formatScore(datum.teamValue)} · ${candidateLabel}: ${formatScore(datum.candidateValue)}`}
            >
              {/* Duas barras adjacentes com 2px de superfície entre elas: o
                  espaço em branco faz a separação, não um contorno. */}
              <div
                className="absolute top-0 left-0 h-3 rounded-r"
                style={{
                  width: `${scalePercent(datum.teamValue)}%`,
                  minWidth: MIN_BAR,
                  background: "var(--series-1)",
                }}
                role="img"
                aria-label={`${datum.label}, ${teamLabel}: ${formatScore(datum.teamValue)} de 5`}
              />
              <div
                className="absolute left-0 h-3 rounded-r"
                style={{
                  top: "calc(0.75rem + 2px)",
                  width: `${scalePercent(datum.candidateValue)}%`,
                  minWidth: MIN_BAR,
                  background: "var(--series-2)",
                }}
                role="img"
                aria-label={`${datum.label}, ${candidateLabel}: ${formatScore(datum.candidateValue)} de 5`}
              />
            </Track>
          </div>
        ))}
      </div>

      <AxisRow />
      <ChanceCaption />
    </ChartFrame>
  );
}
