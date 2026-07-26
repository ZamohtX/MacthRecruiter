import { ChartFrame, DataTable } from "./ChartFrame";
import type { LegendItem } from "./ChartFrame";
import { DIMENSION_SHORT, DIMENSIONS } from "./dimensions";
import { AXIS_TICKS, CHANCE_LEVEL, SCALE_MIN, formatScore, scalePercent } from "./scale";

/**
 * Radar (teia) das 10 soft skills — o gráfico-assinatura do produto.
 *
 * Uma série é o perfil isolado; duas séries sobrepõem candidato e média do time,
 * e onde o polígono do candidato "estica" além do time é exatamente a lacuna que
 * ele cobre. Compartilha a escala 1–5 ancorada no acaso com os outros gráficos:
 * o raio de um valor usa `scalePercent`, então 3.0 (nível do acaso) cai no mesmo
 * anel em todo lugar, e os eixos seguem a ordem canônica de `DIMENSIONS`.
 */
export interface RadarSeries {
  label: string;
  /** Papel CSS da série, ex.: "var(--series-1)". Nunca hex solto. */
  color: string;
  scores: Record<string, number>;
}

interface RadarProps {
  title: string;
  subtitle?: string;
  series: RadarSeries[];
  dimensions?: readonly string[];
}

// Geometria em unidades do viewBox. O raio máximo deixa folga até a borda para os
// rótulos dos eixos não serem cortados.
const BOX = 360;
const CENTER = BOX / 2;
const MAX_R = 118;
const LABEL_R = 132;

/** Ângulo do eixo `i`: começa no topo (−90°) e gira no sentido horário. */
function angleFor(index: number, total: number): number {
  return -Math.PI / 2 + (index / total) * 2 * Math.PI;
}

function pointFor(index: number, total: number, radius: number): [number, number] {
  const theta = angleFor(index, total);
  return [CENTER + radius * Math.cos(theta), CENTER + radius * Math.sin(theta)];
}

/** Raio do valor na escala 1–5 — reusa o mapeamento 0–100% dos outros gráficos. */
function radiusFor(value: number): number {
  return (scalePercent(value) / 100) * MAX_R;
}

function polygonPoints(radii: number[], total: number): string {
  return radii.map((radius, index) => pointFor(index, total, radius).join(",")).join(" ");
}

export function Radar({ title, subtitle, series, dimensions = DIMENSIONS }: RadarProps) {
  const total = dimensions.length;

  const legend: LegendItem[] = series.map((serie) => ({ label: serie.label, color: serie.color }));

  const table = (
    <DataTable
      headers={["Dimensão", ...series.map((serie) => serie.label)]}
      rows={dimensions.map((dimension) => [
        dimension,
        ...series.map((serie) => formatScore(serie.scores[dimension])),
      ])}
    />
  );

  const ariaLabel = `${title}. Radar de ${total} competências para ${series
    .map((serie) => serie.label)
    .join(" e ")}.`;

  return (
    <ChartFrame title={title} subtitle={subtitle} legend={legend} table={table}>
      <div className="mx-auto" style={{ maxWidth: "26rem" }}>
        <svg viewBox={`0 0 ${BOX} ${BOX}`} className="h-auto w-full" role="img" aria-label={ariaLabel}>
          {/* Anéis da escala: um polígono por marca de 1–5. O anel do acaso (3)
              vem destacado — acima dele é "escolhe bem mais que o acaso". */}
          {AXIS_TICKS.filter((tick) => tick > SCALE_MIN).map((tick) => {
            const radius = radiusFor(tick);
            const isChance = tick === CHANCE_LEVEL;
            return (
              <polygon
                key={`ring-${tick}`}
                points={polygonPoints(dimensions.map(() => radius), total)}
                fill="none"
                stroke={isChance ? "var(--baseline)" : "var(--gridline)"}
                strokeWidth={isChance ? 1.4 : 1}
                strokeDasharray={isChance ? "3 3" : undefined}
              />
            );
          })}

          {/* Eixos (raios) e rótulos por quadrante. */}
          {dimensions.map((dimension, index) => {
            const [ox, oy] = pointFor(index, total, MAX_R);
            const [lx, ly] = pointFor(index, total, LABEL_R);
            const cos = Math.cos(angleFor(index, total));
            const sin = Math.sin(angleFor(index, total));
            const anchor = cos > 0.1 ? "start" : cos < -0.1 ? "end" : "middle";
            const baseline = sin > 0.1 ? "hanging" : sin < -0.1 ? "auto" : "middle";
            return (
              <g key={`axis-${dimension}`}>
                <line x1={CENTER} y1={CENTER} x2={ox} y2={oy} stroke="var(--gridline)" strokeWidth={1} />
                <text
                  x={lx}
                  y={ly}
                  textAnchor={anchor}
                  dominantBaseline={baseline}
                  style={{ fill: "var(--text-muted)", fontSize: "9px" }}
                >
                  {DIMENSION_SHORT[dimension] ?? dimension}
                </text>
              </g>
            );
          })}

          {/* Marca "3" no eixo do topo, para dar leitura ao anel do acaso. */}
          <text
            x={CENTER + 4}
            y={CENTER - radiusFor(CHANCE_LEVEL)}
            style={{ fill: "var(--text-muted)", fontSize: "7.5px" }}
          >
            3
          </text>

          {/* Polígonos das séries, na ordem passada (time por baixo, candidato por
              cima costuma ler melhor). */}
          {series.map((serie) => {
            const radii = dimensions.map((dimension) => radiusFor(serie.scores[dimension] ?? SCALE_MIN));
            return (
              <g key={`serie-${serie.label}`}>
                <polygon
                  points={polygonPoints(radii, total)}
                  fill={`color-mix(in srgb, ${serie.color} 18%, transparent)`}
                  stroke={serie.color}
                  strokeWidth={2}
                  strokeLinejoin="round"
                />
                {radii.map((radius, index) => {
                  const [px, py] = pointFor(index, total, radius);
                  return (
                    <circle key={`${serie.label}-dot-${index}`} cx={px} cy={py} r={2.5} fill={serie.color}>
                      <title>{`${serie.label} — ${dimensions[index]}: ${formatScore(
                        serie.scores[dimensions[index]],
                      )}`}</title>
                    </circle>
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>

      <p className="mt-3 text-center text-xs" style={{ color: "var(--text-muted)" }}>
        Escala 1–5 ancorada no acaso · o anel tracejado marca 3.0 (nível do acaso).
      </p>
    </ChartFrame>
  );
}
