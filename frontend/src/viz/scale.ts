/**
 * A escala do instrumento e sua leitura.
 *
 * Os escores são **normativos**, ancorados no nível de acaso: 3.0 significa
 * "escolhe as condutas deste fator na frequência que o acaso produziria".
 * Por isso os gráficos crescem do piso real da escala (1.0) e marcam 3.0 como
 * referência — sem essa linha, 4.2 seria lido como "domina a competência",
 * quando significa "escolhe bem mais que o acaso".
 */
export const SCALE_MIN = 1;
export const SCALE_MAX = 5;
export const CHANCE_LEVEL = 3;

/** Posição de um valor dentro da escala, em 0–100%. */
export function scalePercent(value: number): number {
  const clamped = Math.min(SCALE_MAX, Math.max(SCALE_MIN, value));
  return ((clamped - SCALE_MIN) / (SCALE_MAX - SCALE_MIN)) * 100;
}

export const AXIS_TICKS = [1, 2, 3, 4, 5];

export function formatScore(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : value.toFixed(2);
}

export function formatDelta(value: number): string {
  return `${value > 0 ? "+" : value < 0 ? "−" : "±"}${Math.abs(value).toFixed(2)}`;
}

export const DIMENSION_STATUS_LABEL = {
  GAP: "Lacuna",
  ADEQUATE: "Adequado",
  STRENGTH: "Força",
} as const;

/** Ícone junto do rótulo: cor de status nunca carrega significado sozinha. */
export const DIMENSION_STATUS_ICON = {
  GAP: "▼",
  ADEQUATE: "■",
  STRENGTH: "▲",
} as const;

export const DIMENSION_STATUS_COLOR = {
  GAP: "var(--status-critical)",
  ADEQUATE: "var(--text-muted)",
  STRENGTH: "var(--status-good)",
} as const;
