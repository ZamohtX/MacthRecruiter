import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router";

import { api } from "../api/client";
import type { SimulatedCandidate } from "../api/types";
import { AiSummaryCard } from "../components/AiSummaryCard";
import { Button, Callout, Card, Disclosure, ErrorState, InfoTip, PageTitle, Spinner } from "../components/ui";
import { DIMENSIONS } from "../viz/dimensions";
import { Radar } from "../viz/Radar";
import { StatTile, VerdictBadge, verdictDescription } from "../viz/StatTile";

/** Média do time recalculada com o candidato dentro: (soma_atual + candidato)/(N+1). */
function postHireScores(
  teamScores: Record<string, number>,
  candidateScores: Record<string, number>,
  respondentCount: number,
): Record<string, number> {
  const n = respondentCount;
  return Object.fromEntries(
    DIMENSIONS.map((dim) => {
      const team = teamScores[dim] ?? 0;
      const cand = candidateScores[dim] ?? 0;
      return [dim, n > 0 ? (team * n + cand) / (n + 1) : cand];
    }),
  );
}

const TEAM_COLOR = "var(--series-1)";
const CANDIDATE_COLOR = "var(--series-2)";
const EDGE = {
  team_size: 6,
  limit: 24,
  team_name: "Turma Edge",
  job_title: "Pessoa Desenvolvedora — Turma Edge",
} as const;
const EDGE_KEY = ["academy", "edge-team"] as const;

/**
 * Aba Candidatos — a Turma Edge do OxeTech Academy, já montada: um time com os
 * alunos, o diagnóstico aplicado em todos, e o radar de cada candidato (isolado
 * e sobreposto à média do time). Carrega sozinha ao abrir (idempotente: reabrir
 * não cria outra turma); "Gerar outro time" sorteia uma nova. Quando a turma
 * está sem alunos na API (caso atual), um pool sintético equivalente é usado.
 */
export function CandidatesPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Carrega/gera a Turma Edge ao abrir. Idempotente no backend: sempre devolve a
  // mesma turma até pedirem outra. staleTime alto evita refetch a cada foco.
  const edge = useQuery({
    queryKey: EDGE_KEY,
    queryFn: () => api.integrations.simulate({ ...EDGE }),
    staleTime: 5 * 60_000,
  });

  const regenerate = useMutation({
    mutationFn: () => api.integrations.simulate({ ...EDGE, regenerate: true }),
    onSuccess: (fresh) => {
      queryClient.setQueryData(EDGE_KEY, fresh);
      setSelectedId(fresh.candidates[0]?.candidate_id ?? null);
      void queryClient.invalidateQueries({ queryKey: ["teams"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const data = edge.data;
  const busy = edge.isLoading || regenerate.isPending;

  // Seleciona o topo do ranking quando os dados chegam ou mudam.
  useEffect(() => {
    if (data && !data.candidates.some((c) => c.candidate_id === selectedId)) {
      setSelectedId(data.candidates[0]?.candidate_id ?? null);
    }
  }, [data, selectedId]);

  const selected = data?.candidates.find((c) => c.candidate_id === selectedId) ?? null;

  return (
    <div>
      <PageTitle
        title="Candidatos"
        subtitle="A Turma Edge do OxeTech Academy: um time montado com os alunos, o diagnóstico aplicado e cada candidato comparado com a média do time."
        actions={
          <Button onClick={() => regenerate.mutate()} disabled={busy}>
            {regenerate.isPending ? "Gerando…" : "Gerar outro time"}
          </Button>
        }
      />

      {edge.isLoading && <Spinner label="Montando a Turma Edge e aplicando o diagnóstico…" />}

      {edge.isError && <ErrorState error={edge.error} onRetry={() => edge.refetch()} />}

      {data && (
        <div className="space-y-6">
          {data.source === "synthetic" && (
            <Callout tone="info" title="Pool sintético">
              A API do Academy não tem alunos disponíveis nesta turma, então o time foi montado com um
              roster sintético equivalente. Assim que houver alunos reais, a mesma geração passa a usá-los.
            </Callout>
          )}

          {/* ---------------------------------------------------- o time gerado */}
          <div className="grid gap-3 sm:grid-cols-3">
            <StatTile label="Origem" value={data.source === "academy_api" ? "API Academy" : "Sintético"} />
            <StatTile
              label="Responderam o diagnóstico"
              value={String(data.respondent_count)}
              hint="Integrantes do time que compõem a média."
            />
            <StatTile
              label="Candidatos"
              value={String(data.candidates.length)}
              hint="Ranqueados por fit complementar."
            />
          </div>

          <Radar
            title={`Perfil do time: ${data.team_name}`}
            subtitle="A forma média das 10 competências do time — os vales são as lacunas a cobrir."
            series={[{ label: "Média do time", color: TEAM_COLOR, scores: data.team_scores }]}
          />

          <div className="flex flex-wrap gap-2">
            <Link to={`/times/${data.team_id}`}>
              <Button variant="secondary">Ver time gerado</Button>
            </Link>
            <Link to={`/vagas/${data.job_id}`}>
              <Button variant="secondary">Ver vaga e ranking completo</Button>
            </Link>
          </div>

          {/* ------------------------------------------ ranking + detalhe do radar */}
          <div className="grid gap-6 lg:grid-cols-[minmax(0,22rem)_1fr]">
            <CandidateList
              candidates={data.candidates}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />

            {selected && (
              <CandidateDetail
                candidate={selected}
                teamScores={data.team_scores}
                respondentCount={data.respondent_count}
                jobId={data.job_id}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function CandidateList({
  candidates,
  selectedId,
  onSelect,
}: {
  candidates: SimulatedCandidate[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <Card className="p-0">
      <ul>
        {candidates.map((candidate, index) => {
          const active = candidate.candidate_id === selectedId;
          return (
            <li key={candidate.candidate_id} style={{ borderBottom: "1px solid var(--gridline)" }}>
              <button
                type="button"
                onClick={() => onSelect(candidate.candidate_id)}
                aria-current={active}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                style={{ background: active ? "var(--seq-track)" : undefined }}
              >
                <span className="w-5 text-sm tabular" style={{ color: "var(--text-muted)" }}>
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                    {candidate.name}
                  </span>
                  <span className="block truncate text-xs" style={{ color: "var(--text-muted)" }}>
                    {candidate.techs.slice(0, 3).join(" · ") || "—"}
                  </span>
                </span>
                <span className="text-right">
                  <span className="block text-sm font-semibold tabular" style={{ color: "var(--text-primary)" }}>
                    {candidate.fit_score.toFixed(1)}
                  </span>
                  <VerdictBadge verdict={candidate.verdict} compact />
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function CandidateDetail({
  candidate,
  teamScores,
  respondentCount,
  jobId,
}: {
  candidate: SimulatedCandidate;
  teamScores: Record<string, number>;
  respondentCount: number;
  jobId: string;
}) {
  const afterScores = postHireScores(teamScores, candidate.candidate_scores, respondentCount);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
            {candidate.name}
          </h2>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            {verdictDescription(candidate.verdict)}
          </p>
        </div>
        <VerdictBadge verdict={candidate.verdict} />
      </div>

      <AiSummaryCard jobId={jobId} candidateId={candidate.candidate_id} />

      <div className="grid gap-3 sm:grid-cols-2">
        <StatTile
          label="Fit complementar"
          value={candidate.fit_score.toFixed(1)}
          meter={candidate.fit_score}
          meterColor={TEAM_COLOR}
          hint="Quanto cobre as lacunas do time. É o critério de ranqueamento."
        >
          <InfoTip term="fit complementar" />
        </StatTile>
        <StatTile
          label="Semelhança com o time"
          value={candidate.supplementary_fit_index.toFixed(1)}
          meter={candidate.supplementary_fit_index}
          meterColor={CANDIDATE_COLOR}
          hint="Alto com fit baixo significa contratar mais do mesmo."
        >
          <InfoTip term="semelhança com o time" />
        </StatTile>
      </div>

      {/* Os 2 radares combinados: sobreposição e pós-contratação. */}
      <Radar
        title="Candidato × média do time"
        subtitle="Onde o candidato estica além do time é a lacuna que ele cobre; onde encolhe, dilui uma força."
        series={[
          { label: "Média do time", color: TEAM_COLOR, scores: teamScores },
          { label: candidate.name, color: CANDIDATE_COLOR, scores: candidate.candidate_scores },
        ]}
      />

      <Radar
        title="Time hoje → depois da contratação"
        subtitle="Como fica a média do time se esta pessoa entrar."
        series={[
          { label: "Time hoje", color: TEAM_COLOR, scores: teamScores },
          { label: "Time depois", color: "var(--status-good)", scores: afterScores },
        ]}
      />

      <Link to={`/vagas/${jobId}/candidatos/${candidate.candidate_id}`}>
        <Button variant="secondary">Ver simulação completa (antes → depois)</Button>
      </Link>

      <Disclosure summary="Ver o radar isolado do candidato">
        <Radar
          title="Radar do candidato"
          subtitle="O perfil isolado das 10 competências deste candidato."
          series={[{ label: candidate.name, color: CANDIDATE_COLOR, scores: candidate.candidate_scores }]}
        />
        {candidate.gaps_filled.length > 0 && (
          <p className="text-sm" style={{ color: "var(--status-good)" }}>
            ▲ Cobre: {candidate.gaps_filled.join(", ")}
          </p>
        )}
      </Disclosure>
    </div>
  );
}
