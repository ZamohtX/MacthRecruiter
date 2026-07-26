import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { api } from "../api/client";
import type { CandidateSummary } from "../api/types";
import { Button, Callout, Card, ConfirmButton, EmptyState, ErrorState, PageTitle, Spinner } from "../components/ui";
import { StatTile, VerdictBadge } from "../viz/StatTile";

function CandidateRow({
  candidate,
  jobId,
  onRemove,
  removing,
}: {
  candidate: CandidateSummary;
  jobId: string;
  onRemove: (candidateId: string) => void;
  removing: boolean;
}) {
  const fit = candidate.fit_score;
  const supplementary = candidate.supplementary_fit_index;

  return (
    <li className="rounded-lg p-4" style={{ border: "1px solid var(--hairline)" }}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium" style={{ color: "var(--text-primary)" }}>
            {candidate.candidate_name}
          </p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            {candidate.candidate_email}
          </p>
        </div>
        {candidate.verdict && <VerdictBadge verdict={candidate.verdict} />}
      </div>

      {candidate.soft_skills_completed ? (
        <>
          {/* Duas medidas lado a lado: é a comparação que o produto existe para
              tornar visível. Trilhos são passos mais claros da mesma rampa. */}
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <div className="mb-1 flex items-baseline justify-between text-xs">
                <span style={{ color: "var(--text-secondary)" }}>Fit complementar</span>
                <span className="tabular font-medium" style={{ color: "var(--text-primary)" }}>
                  {fit?.toFixed(1)}
                </span>
              </div>
              <div
                className="h-1.5 overflow-hidden rounded-full"
                style={{ background: "color-mix(in srgb, var(--series-1) 22%, transparent)" }}
              >
                <div className="h-full rounded-full" style={{ width: `${fit ?? 0}%`, background: "var(--series-1)" }} />
              </div>
            </div>

            <div>
              <div className="mb-1 flex items-baseline justify-between text-xs">
                <span style={{ color: "var(--text-secondary)" }}>Semelhança com o time</span>
                <span className="tabular font-medium" style={{ color: "var(--text-primary)" }}>
                  {supplementary?.toFixed(1)}
                </span>
              </div>
              <div
                className="h-1.5 overflow-hidden rounded-full"
                style={{ background: "color-mix(in srgb, var(--series-2) 22%, transparent)" }}
              >
                <div
                  className="h-full rounded-full"
                  style={{ width: `${supplementary ?? 0}%`, background: "var(--series-2)" }}
                />
              </div>
            </div>
          </div>

          {candidate.gaps_filled.length > 0 ? (
            <p className="mt-3 text-xs" style={{ color: "var(--text-secondary)" }}>
              <span aria-hidden style={{ color: "var(--status-good)" }}>
                ▲{" "}
              </span>
              Cobre: {candidate.gaps_filled.join(", ")}
            </p>
          ) : (
            <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
              Não cobre nenhuma lacuna do time.
            </p>
          )}
        </>
      ) : (
        <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
          Ainda não respondeu o teste — sem perfil para comparar.
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Link to={`/vagas/${jobId}/candidatos/${candidate.candidate_id}`}>
          <Button variant="secondary" disabled={!candidate.soft_skills_completed}>
            Ver simulação
          </Button>
        </Link>
        <ConfirmButton
          label="Remover"
          confirmLabel="Remover da vaga?"
          disabled={removing}
          onConfirm={() => onRemove(candidate.candidate_id)}
        />
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {candidate.status}
        </span>
      </div>
    </li>
  );
}

export function JobDetailPage() {
  const { jobId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [onlyComplementary, setOnlyComplementary] = useState(false);

  const job = useQuery({ queryKey: ["job", jobId], queryFn: () => api.jobs.get(jobId) });
  const candidates = useQuery({
    queryKey: ["job", jobId, "candidates"],
    queryFn: () => api.jobs.candidates(jobId),
  });

  const removeJob = useMutation({
    mutationFn: () => api.jobs.remove(jobId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      navigate("/vagas", { replace: true });
    },
  });

  const removeCandidate = useMutation({
    mutationFn: (candidateId: string) => api.jobs.removeApplication(jobId, candidateId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["job", jobId] });
    },
  });

  if (job.isPending) return <Spinner />;
  if (job.isError) return <ErrorState error={job.error} onRetry={() => job.refetch()} />;

  const applyUrl = `${window.location.origin}/vaga/${jobId}`;
  const list = candidates.data ?? [];
  const visible = onlyComplementary ? list.filter((c) => c.verdict === "COMPLEMENTARY") : list;
  const assessed = list.filter((c) => c.soft_skills_completed);

  return (
    <div className="space-y-6">
      <PageTitle
        title={job.data.title}
        subtitle={
          <>
            Time <Link to={`/times/${job.data.team_id}`} className="underline">{job.data.team_name}</Link> ·{" "}
            {job.data.application_count} candidatura(s)
          </>
        }
        actions={
          <ConfirmButton
            label="Excluir vaga"
            confirmLabel="Excluir a vaga?"
            disabled={removeJob.isPending}
            onConfirm={() => removeJob.mutate()}
          />
        }
      />

      {!job.data.team_assessment_ready && (
        <Callout tone="critical" title="O time ainda não respondeu o diagnóstico">
          Sem o perfil do time não há lacuna a cobrir: o fit de qualquer candidato sai marcado como
          <strong> sem diagnóstico</strong> e não representa complementaridade.
        </Callout>
      )}

      <Callout tone="info" title="Link de candidatura">
        <div className="flex flex-wrap items-center gap-2">
          <code
            className="rounded px-2 py-1 text-xs break-all"
            style={{ background: "var(--page-plane)", color: "var(--text-primary)" }}
          >
            {applyUrl}
          </code>
          <Button variant="secondary" onClick={() => void navigator.clipboard.writeText(applyUrl)}>
            Copiar
          </Button>
        </div>
      </Callout>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatTile label="Candidaturas" value={String(list.length)} />
        <StatTile
          label="Testes concluídos"
          value={String(assessed.length)}
          meter={list.length ? (assessed.length / list.length) * 100 : 0}
        />
        <StatTile
          label="Complementares"
          value={String(list.filter((c) => c.verdict === "COMPLEMENTARY").length)}
          hint="Cobrem as lacunas de forma decisiva."
        />
      </div>

      {/* Um filtro só, acima de tudo que ele afeta. */}
      <div className="flex items-center gap-2">
        <input
          id="only-complementary"
          type="checkbox"
          checked={onlyComplementary}
          onChange={(event) => setOnlyComplementary(event.target.checked)}
          className="h-4 w-4 accent-[var(--seq-fill)]"
        />
        <label htmlFor="only-complementary" className="text-sm" style={{ color: "var(--text-secondary)" }}>
          Mostrar só candidatos complementares
        </label>
      </div>

      <Card>
        <h3 className="mb-1 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          Candidatos por fit complementar
        </h3>
        <p className="mb-4 text-xs" style={{ color: "var(--text-muted)" }}>
          Ordenados por quanto cobrem as lacunas do time. Semelhança alta com fit baixo significa
          contratar mais do mesmo.
        </p>

        {candidates.isPending && <Spinner />}
        {candidates.isError && <ErrorState error={candidates.error} onRetry={() => candidates.refetch()} />}

        {candidates.isSuccess &&
          (visible.length === 0 ? (
            <EmptyState
              title={onlyComplementary ? "Nenhum candidato complementar" : "Nenhuma candidatura ainda"}
              description={
                onlyComplementary
                  ? "Tire o filtro para ver todos os candidatos."
                  : "Compartilhe o link de candidatura acima."
              }
            />
          ) : (
            <ul className="space-y-3">
              {visible.map((candidate) => (
                <CandidateRow
                  key={candidate.candidate_id}
                  candidate={candidate}
                  jobId={jobId}
                  onRemove={(candidateId) => removeCandidate.mutate(candidateId)}
                  removing={removeCandidate.isPending}
                />
              ))}
            </ul>
          ))}
      </Card>
    </div>
  );
}

export function JobsPage() {
  const queryClient = useQueryClient();
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.jobs.list });

  const removeJob = useMutation({
    mutationFn: (jobId: string) => api.jobs.remove(jobId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });

  return (
    <div>
      <PageTitle title="Vagas" subtitle="Vagas dos times de que você é responsável." />
      {jobs.isPending && <Spinner />}
      {jobs.isError && <ErrorState error={jobs.error} onRetry={() => jobs.refetch()} />}
      {jobs.isSuccess &&
        (jobs.data.length === 0 ? (
          <EmptyState
            title="Nenhuma vaga aberta"
            description="Abra uma vaga a partir da página de um time, depois que o diagnóstico estiver aplicado."
          />
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {jobs.data.map((job) => (
              <li
                key={job.id}
                className="flex items-center justify-between gap-3 rounded-xl p-4"
                style={{ background: "var(--surface-1)", border: "1px solid var(--hairline)" }}
              >
                <Link to={`/vagas/${job.id}`} className="min-w-0 flex-1">
                  <p className="truncate font-medium" style={{ color: "var(--text-primary)" }}>
                    {job.title}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                    Aberta em {new Date(job.created_at).toLocaleDateString("pt-BR")}
                  </p>
                </Link>
                <ConfirmButton
                  label="Excluir"
                  confirmLabel="Excluir a vaga?"
                  disabled={removeJob.isPending}
                  onConfirm={() => removeJob.mutate(job.id)}
                />
              </li>
            ))}
          </ul>
        ))}
    </div>
  );
}
