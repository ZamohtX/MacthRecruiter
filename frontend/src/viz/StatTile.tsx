import type { ReactNode } from "react";

import type { FitVerdict } from "../api/types";

interface StatTileProps {
  label: string;
  value: string;
  hint?: string;
  /** Medidor 0–100. O track é um passo mais claro da mesma rampa. */
  meter?: number;
  meterColor?: string;
  children?: ReactNode;
}

/**
 * Um número é um número — não um gráfico de uma barra.
 *
 * Valor em figuras proporcionais (o padrão da fonte): `tabular-nums` deixa
 * números grandes frouxos, e só vale em colunas que precisam alinhar.
 */
export function StatTile({ label, value, hint, meter, meterColor = "var(--seq-fill)", children }: StatTileProps) {
  return (
    <div
      className="rounded-xl p-4"
      style={{ background: "var(--surface-1)", border: "1px solid var(--hairline)" }}
    >
      <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
        {label}
      </p>
      <p className="mt-1 text-3xl font-semibold" style={{ color: "var(--text-primary)" }}>
        {value}
      </p>

      {meter !== undefined && (
        <div
          className="mt-3 h-1.5 w-full overflow-hidden rounded-full"
          // Trilho = passo mais claro da própria rampa do preenchimento, para o
          // estado ser legível ao longo de toda a barra nos dois temas.
          style={{ background: `color-mix(in srgb, ${meterColor} 22%, transparent)` }}
          role="img"
          aria-label={`${label}: ${value} de 100`}
        >
          <div
            className="h-full rounded-full"
            style={{ width: `${Math.min(100, Math.max(0, meter))}%`, background: meterColor }}
          />
        </div>
      )}

      {hint && (
        <p className="mt-2 text-[11px] leading-snug" style={{ color: "var(--text-muted)" }}>
          {hint}
        </p>
      )}
      {children}
    </div>
  );
}

/** Ícone + rótulo + cor. Cor de status nunca carrega o significado sozinha. */
const VERDICT_PRESENTATION: Record<
  FitVerdict,
  { icon: string; label: string; color: string; description: string }
> = {
  COMPLEMENTARY: {
    icon: "▲",
    label: "Complementar",
    color: "var(--status-good)",
    description: "Cobre as lacunas do time de forma decisiva.",
  },
  BALANCED: {
    icon: "■",
    label: "Equilibrado",
    color: "var(--text-muted)",
    description: "Contribui, mas sem fechar lacuna de forma decisiva.",
  },
  EXCESSIVE_SUPPLEMENTARY: {
    icon: "◆",
    label: "Suplementar em excesso",
    color: "var(--status-serious)",
    description: "Mais do mesmo: reforça as forças e deixa as lacunas descobertas.",
  },
  BELOW_MINIMUM: {
    icon: "▼",
    label: "Abaixo do mínimo",
    color: "var(--status-critical)",
    description: "Deixa uma competência ausente do time como encontrou.",
  },
  INSUFFICIENT_TEAM_DATA: {
    icon: "!",
    label: "Sem diagnóstico do time",
    color: "var(--status-warning)",
    description: "Ninguém do time respondeu — não há complementaridade a medir.",
  },
};

export function VerdictBadge({ verdict, compact = false }: { verdict: FitVerdict; compact?: boolean }) {
  const presentation = VERDICT_PRESENTATION[verdict];

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs"
      style={{ border: `1px solid ${presentation.color}`, color: "var(--text-primary)" }}
      title={presentation.description}
    >
      <span aria-hidden style={{ color: presentation.color }}>
        {presentation.icon}
      </span>
      {presentation.label}
      {!compact && <span className="sr-only">. {presentation.description}</span>}
    </span>
  );
}

export function verdictDescription(verdict: FitVerdict): string {
  return VERDICT_PRESENTATION[verdict].description;
}
