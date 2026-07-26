import { useId, useState } from "react";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

import { ApiError } from "../api/client";
import { GLOSSARY } from "./glossary";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  // --seq-fill é o verde da marca — texto escuro (não branco) para manter
  // contraste sobre um acento tão claro.
  primary: "bg-[var(--seq-fill)] text-[var(--brand-void)] font-semibold hover:opacity-90",
  secondary: "border border-[var(--hairline)] hover:bg-black/5 dark:hover:bg-white/10",
  ghost: "hover:bg-black/5 dark:hover:bg-white/10",
  danger: "border border-[var(--status-critical)] hover:bg-[var(--status-critical)]/10",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-opacity disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_STYLES[variant]} ${className}`}
      style={variant === "primary" ? undefined : { color: "var(--text-primary)" }}
    />
  );
}

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--seq-fill)] ${className}`}
      style={{
        background: "var(--surface-1)",
        color: "var(--text-primary)",
        border: "1px solid var(--hairline)",
      }}
    />
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-xl p-5 ${className}`}
      style={{ background: "var(--surface-1)", border: "1px solid var(--hairline)" }}
    >
      {children}
    </div>
  );
}

export function PageTitle({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
          {title}
        </h1>
        {subtitle && (
          <div className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
            {subtitle}
          </div>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}

export function Spinner({ label = "Carregando…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12" role="status">
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
        style={{ color: "var(--text-muted)" }}
        aria-hidden
      />
      <span className="text-sm" style={{ color: "var(--text-muted)" }}>
        {label}
      </span>
    </div>
  );
}

/** Mensagem de erro que distingue 403 e 404 do resto — o usuário precisa saber
 *  se o problema é permissão, recurso inexistente ou falha real. */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const status = error instanceof ApiError ? error.status : null;
  const message = error instanceof Error ? error.message : "Erro desconhecido.";

  const title =
    status === 403
      ? "Você não tem acesso a este recurso"
      : status === 404
        ? "Recurso não encontrado"
        : "Algo deu errado";

  return (
    <Card>
      <p className="text-sm font-medium" style={{ color: "var(--status-critical)" }}>
        {title}
      </p>
      <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
        {message}
      </p>
      {onRetry && (
        <Button variant="secondary" className="mt-3" onClick={onRetry}>
          Tentar de novo
        </Button>
      )}
    </Card>
  );
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <Card className="text-center">
      <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
        {title}
      </p>
      {description && (
        <p className="mx-auto mt-1 max-w-md text-sm" style={{ color: "var(--text-secondary)" }}>
          {description}
        </p>
      )}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </Card>
  );
}

/** Aviso com ícone + rótulo: cor sozinha nunca carrega o significado. */
export function Callout({
  tone = "warning",
  title,
  children,
}: {
  tone?: "warning" | "critical" | "good" | "info";
  title: string;
  children?: ReactNode;
}) {
  const presentation = {
    warning: { color: "var(--status-warning)", icon: "!" },
    critical: { color: "var(--status-critical)", icon: "▼" },
    good: { color: "var(--status-good)", icon: "▲" },
    info: { color: "var(--text-muted)", icon: "i" },
  }[tone];

  return (
    <div
      className="rounded-lg p-3 text-sm"
      style={{ background: "var(--surface-1)", border: `1px solid ${presentation.color}` }}
    >
      <p className="flex items-center gap-2 font-medium" style={{ color: "var(--text-primary)" }}>
        <span
          aria-hidden
          className="flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold text-white"
          style={{ background: presentation.color }}
        >
          {presentation.icon}
        </span>
        {title}
      </p>
      {children && (
        <div className="mt-1.5 pl-6 text-sm" style={{ color: "var(--text-secondary)" }}>
          {children}
        </div>
      )}
    </div>
  );
}

export function ProgressBar({ value, max, label }: { value: number; max: number; label: string }) {
  const percent = max > 0 ? (value / max) * 100 : 0;
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between text-xs">
        <span style={{ color: "var(--text-secondary)" }}>{label}</span>
        <span className="tabular" style={{ color: "var(--text-muted)" }}>
          {value} / {max}
        </span>
      </div>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full"
        style={{ background: "color-mix(in srgb, var(--seq-fill) 22%, transparent)" }}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label}
      >
        <div
          className="h-full rounded-full transition-[width] duration-300"
          style={{ width: `${percent}%`, background: "var(--seq-fill)" }}
        />
      </div>
    </div>
  );
}

/**
 * Botão de exclusão em dois passos. O primeiro clique não apaga nada — troca para
 * "Confirmar? Sim / Não". Evita `confirm()` nativo (feio, fora do tema) e o peso de
 * um modal, mantendo a ação destrutiva atrás de uma confirmação explícita.
 */
export function ConfirmButton({
  onConfirm,
  label = "Excluir",
  confirmLabel = "Confirmar exclusão?",
  disabled,
  className = "",
}: {
  onConfirm: () => void;
  label?: string;
  confirmLabel?: string;
  disabled?: boolean;
  className?: string;
}) {
  const [armed, setArmed] = useState(false);

  if (!armed) {
    return (
      <Button variant="danger" disabled={disabled} className={className} onClick={() => setArmed(true)}>
        {label}
      </Button>
    );
  }

  return (
    <span className="inline-flex items-center gap-2">
      <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
        {confirmLabel}
      </span>
      <Button
        variant="danger"
        disabled={disabled}
        onClick={() => {
          setArmed(false);
          onConfirm();
        }}
      >
        Sim
      </Button>
      <Button variant="ghost" onClick={() => setArmed(false)}>
        Não
      </Button>
    </span>
  );
}

/**
 * Bloco recolhível para a "análise completa" — a divulgação progressiva mantém a
 * conclusão à vista e guarda aqui o aprofundamento. Baseado em `<details>` para
 * herdar acessibilidade e funcionar sem estado externo.
 */
export function Disclosure({
  summary,
  children,
  defaultOpen = false,
}: {
  summary: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details open={defaultOpen} className="group">
      <summary
        className="flex cursor-pointer list-none items-center gap-2 rounded-lg px-1 py-2 text-sm font-medium select-none"
        style={{ color: "var(--text-secondary)" }}
      >
        <span aria-hidden className="transition-transform group-open:rotate-90">
          ▸
        </span>
        {summary}
      </summary>
      <div className="mt-3 space-y-6">{children}</div>
    </details>
  );
}

/**
 * "?" ao lado de um termo, com a definição curta do glossário. Mostra no hover e no
 * foco (teclado), e o texto vai no `title` nativo como reforço. O termo em si
 * continua visível; o InfoTip só explica.
 */
export function InfoTip({ term }: { term: keyof typeof GLOSSARY }) {
  const definition = GLOSSARY[term];
  const id = useId();

  return (
    <span className="group relative inline-flex">
      <button
        type="button"
        aria-label={`O que é ${term}`}
        aria-describedby={id}
        className="inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] leading-none"
        style={{ border: "1px solid var(--baseline)", color: "var(--text-muted)" }}
      >
        ?
      </button>
      <span
        id={id}
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-1 w-56 -translate-x-1/2 rounded-lg p-2 text-xs opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
        style={{
          background: "var(--surface-1)",
          border: "1px solid var(--hairline)",
          color: "var(--text-secondary)",
        }}
      >
        {definition}
      </span>
    </span>
  );
}
