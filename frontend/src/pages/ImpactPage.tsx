import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router";

import { api } from "../api/client";
import type { Contribution } from "../api/types";
import { AiSummaryCard } from "../components/AiSummaryCard";
import { Button, Callout, Card, Disclosure, ErrorState, InfoTip, PageTitle, Spinner } from "../components/ui";
import { ComparisonBars } from "../viz/BarChart";
import { Dumbbell } from "../viz/Dumbbell";
import { Radar } from "../viz/Radar";
import { StatTile, VerdictBadge, verdictDescription } from "../viz/StatTile";
import { formatDelta } from "../viz/scale";

/** Ícone + rótulo para cada tipo de contribuição — cor nunca sozinha. */
const CONTRIBUTION: Record<Contribution, { icon: string; color: string; label: string }> = {
  FILLS_GAP: { icon: "▲", color: "var(--status-good)", label: "Cobre a lacuna" },
  PARTIAL_LIFT: { icon: "◔", color: "var(--status-warning)", label: "Melhora, mas não fecha" },
  REDUNDANT: { icon: "◆", color: "var(--status-serious)", label: "Reforço redundante" },
  AGGRAVATES_GAP: { icon: "▼", color: "var(--status-critical)", label: "Aprofunda a lacuna" },
  DILUTES_STRENGTH: { icon: "▽", color: "var(--status-serious)", label: "Dilui uma força" },
  NEUTRAL: { icon: "■", color: "var(--text-muted)", label: "Sem efeito relevante" },
};

export function ImpactPage() {
  const { jobId = "", candidateId = "" } = useParams();
  const queryClient = useQueryClient();

  // O endpoint é POST porque calcula sob demanda; para a UI é uma leitura.
  const impact = useQuery({
    queryKey: ["impact", jobId, candidateId],
    queryFn: () => api.jobs.impact(jobId, candidateId),
  });

  const hire = useMutation({
    mutationFn: () => api.jobs.hire(jobId, candidateId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["job", jobId] });
      void queryClient.invalidateQueries({ queryKey: ["team"] });
      void queryClient.invalidateQueries({ queryKey: ["impact", jobId, candidateId] });
    },
  });

  const reject = useMutation({
    mutationFn: () => api.jobs.updateStatus(jobId, candidateId, "REJECTED"),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["job", jobId, "candidates"] }),
  });

  if (impact.isPending) return <Spinner label="Calculando a simulação…" />;
  if (impact.isError) return <ErrorState error={impact.error} onRetry={() => impact.refetch()} />;

  const data = impact.data;
  const { simulation } = data;

  const dimensions = Object.keys(simulation.current_team_scores).sort();

  const comparison = dimensions.map((dimension) => ({
    label: dimension,
    teamValue: simulation.current_team_scores[dimension] ?? 0,
    candidateValue: data.candidate_scores[dimension] ?? 0,
    status: data.insights.find((insight) => insight.dimension === dimension)?.status,
  }));

  const dumbbell = dimensions.map((dimension) => ({
    label: dimension,
    before: simulation.current_team_scores[dimension] ?? 0,
    after: simulation.simulated_team_scores[dimension] ?? 0,
  }));

  const notableInsights = data.insights.filter((insight) => insight.contribution !== "NEUTRAL");

  return (
    <div className="space-y-6">
      <PageTitle
        title={data.candidate_name}
        subtitle={
          <>
            Simulação pós-contratação ·{" "}
            <Link to={`/vagas/${jobId}`} className="underline">
              voltar à vaga
            </Link>
          </>
        }
        actions={<VerdictBadge verdict={data.verdict} />}
      />

      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        {verdictDescription(data.verdict)}
      </p>

      <AiSummaryCard jobId={jobId!} candidateId={data.candidate_id} />

      {/* --------------------------------------- os 2 números que importam */}
      <div className="grid gap-3 sm:grid-cols-2">
        <StatTile
          label="Fit complementar"
          value={data.complementary_fit_score.toFixed(1)}
          meter={data.complementary_fit_score}
          meterColor="var(--series-1)"
          hint="Quanto cobre as lacunas do time. É o critério de ranqueamento."
        >
          <InfoTip term="fit complementar" />
        </StatTile>
        <StatTile
          label="Semelhança com o time"
          value={data.supplementary_fit_index.toFixed(1)}
          meter={data.supplementary_fit_index}
          meterColor="var(--series-2)"
          hint="Alto com fit baixo significa contratar mais do mesmo."
        >
          <InfoTip term="semelhança com o time" />
        </StatTile>
      </div>

      {/* ------------------------------------- os 2 radares (o essencial visual) */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Radar
          title="Candidato × time hoje"
          subtitle="Onde o candidato estica além do time é a lacuna que ele cobre."
          series={[
            { label: "Time hoje", color: "var(--series-1)", scores: simulation.current_team_scores },
            { label: data.candidate_name, color: "var(--series-2)", scores: data.candidate_scores },
          ]}
        />
        <Radar
          title={`Time hoje → depois (${simulation.current_team_size} → ${simulation.new_team_size})`}
          subtitle="Como fica a média do time se esta pessoa entrar."
          series={[
            { label: "Time hoje", color: "var(--series-1)", scores: simulation.current_team_scores },
            { label: "Time depois", color: "var(--status-good)", scores: simulation.simulated_team_scores },
          ]}
        />
      </div>

      {/* ------------------- aprofundamento recolhido (divulgação progressiva) */}
      <Disclosure summary="Ver análise completa">
        <div className="grid gap-3 sm:grid-cols-2">
          <StatTile
            label="Cobertura de lacunas"
            value={data.gap_coverage === null ? "—" : `${(data.gap_coverage * 100).toFixed(0)}%`}
            hint="Ponderada pelo tamanho de cada lacuna."
          >
            <InfoTip term="cobertura de lacunas" />
          </StatTile>
          <StatTile
            label="Redundância"
            value={data.redundancy === null ? "—" : `${(data.redundancy * 100).toFixed(0)}%`}
            hint="Quanto da força do candidato só duplica o que o time já tem."
          >
            <InfoTip term="redundância" />
          </StatTile>
        </div>

        {data.risk_flags.length > 0 && (
          <Callout tone="warning" title={`${data.risk_flags.length} ponto(s) de atenção`}>
            <ul className="list-disc space-y-1 pl-4">
              {data.risk_flags.map((flag) => (
                <li key={flag}>{flag}</li>
              ))}
            </ul>
          </Callout>
        )}

        <ComparisonBars
          title="Time hoje × candidato"
          subtitle="Onde os dois perfis divergem é onde a contratação muda a composição."
          data={comparison}
        />

        <Dumbbell
          title={`Perfil do time: ${simulation.current_team_size} → ${simulation.new_team_size} pessoas`}
          subtitle="O que acontece com cada competência se esta pessoa entrar."
          data={dumbbell}
        />

        <Card>
          <h3 className="mb-1 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            Leitura dimensão a dimensão
          </h3>
          <p className="mb-4 text-xs" style={{ color: "var(--text-muted)" }}>
            Toda afirmação abaixo é rastreável até as notas que a geraram — o ganho e o custo aparecem
            com o mesmo destaque.
          </p>

          <ul className="space-y-2">
            {(notableInsights.length > 0 ? notableInsights : data.insights).map((insight) => {
              const presentation = CONTRIBUTION[insight.contribution];
              return (
                <li key={insight.dimension} className="flex gap-3 rounded-lg p-3" style={{ border: "1px solid var(--hairline)" }}>
                  <span aria-hidden className="mt-0.5 shrink-0" style={{ color: presentation.color }}>
                    {presentation.icon}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                        {insight.dimension}
                      </span>
                      <span
                        className="tabular text-xs"
                        style={{ color: insight.delta > 0 ? "var(--delta-up-good)" : insight.delta < 0 ? "var(--diverge-neg)" : "var(--text-muted)" }}
                      >
                        {formatDelta(insight.delta)}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
                      {presentation.label}
                    </p>
                    <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                      {insight.explanation}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      </Disclosure>

      {/* -------------------------------------------------------- decisão */}
      <Card>
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          Decisão
        </h3>
        <p className="mt-1 mb-4 text-sm" style={{ color: "var(--text-secondary)" }}>
          O sistema ordena e explica; quem decide é você. Ao contratar, a pessoa entra no time e
          passa a compor o diagnóstico — a simulação vira o perfil real.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => hire.mutate()} disabled={hire.isPending || hire.isSuccess}>
            {hire.isSuccess ? "Contratado" : hire.isPending ? "Contratando…" : "Contratar"}
          </Button>
          <Button variant="danger" onClick={() => reject.mutate()} disabled={reject.isPending || reject.isSuccess}>
            {reject.isSuccess ? "Reprovado" : "Reprovar"}
          </Button>
        </div>
        {hire.isError && (
          <p className="mt-3 text-sm" style={{ color: "var(--status-critical)" }}>
            {hire.error instanceof Error ? hire.error.message : "Erro ao contratar."}
          </p>
        )}
        {hire.isSuccess && (
          <div className="mt-3">
            <p className="mb-2 text-sm" style={{ color: "var(--status-good)" }}>
              Pessoa adicionada ao time — o perfil do time já reflete a contratação.
            </p>
            <Link to={`/vagas/${jobId}`}>
              <Button variant="secondary">Voltar à vaga</Button>
            </Link>
          </div>
        )}
      </Card>
    </div>
  );
}
