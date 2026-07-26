import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";

/**
 * Resumo do candidato em linguagem simples — a "conclusão" que abre a tela.
 *
 * Traduz a análise de fit (números, lacunas, veredito) em duas ou três frases.
 * Vem do Gemini; se ele estiver fora, o backend devolve um resumo-regra com os
 * mesmos dados (`source: "fallback"`), então o card nunca fica vazio nem quebra.
 */
export function AiSummaryCard({ jobId, candidateId }: { jobId: string; candidateId: string }) {
  const summary = useQuery({
    queryKey: ["ai-summary", jobId, candidateId],
    queryFn: () => api.jobs.aiSummary(jobId, candidateId),
    staleTime: Infinity,
  });

  return (
    <section
      className="rounded-xl p-5"
      style={{
        background: "color-mix(in srgb, var(--seq-fill) 8%, var(--surface-1))",
        border: "1px solid color-mix(in srgb, var(--seq-fill) 35%, var(--hairline))",
      }}
    >
      <div className="mb-2 flex items-center gap-2">
        <span aria-hidden>✨</span>
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          Resumo do candidato
        </h3>
      </div>

      {summary.isLoading && (
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Gerando resumo…
        </p>
      )}

      {summary.isError && (
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Não foi possível gerar o resumo agora. Veja a análise completa abaixo.
        </p>
      )}

      {summary.data && (
        <>
          <p className="text-base leading-relaxed" style={{ color: "var(--text-primary)" }}>
            {summary.data.summary}
          </p>
          <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
            {summary.data.source === "ai"
              ? "Gerado por IA · apoia, não substitui a decisão."
              : "Resumo automático a partir dos dados de fit."}
          </p>
        </>
      )}
    </section>
  );
}
