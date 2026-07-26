import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { api } from "../api/client";
import {
  Button,
  Callout,
  Card,
  ConfirmButton,
  Disclosure,
  ErrorState,
  InfoTip,
  Input,
  PageTitle,
  Spinner,
} from "../components/ui";
import { ProfileBars } from "../viz/BarChart";
import { Radar } from "../viz/Radar";
import { StatTile } from "../viz/StatTile";
import { DIMENSION_STATUS_COLOR, DIMENSION_STATUS_ICON, DIMENSION_STATUS_LABEL } from "../viz/scale";

export function TeamDetailPage() {
  const { teamId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);
  const [jobTitle, setJobTitle] = useState("");

  const invalidateTeam = () => {
    void queryClient.invalidateQueries({ queryKey: ["team", teamId] });
  };

  const removeTeam = useMutation({
    mutationFn: () => api.teams.remove(teamId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["teams"] });
      navigate("/", { replace: true });
    },
  });

  const removeMember = useMutation({
    mutationFn: (userId: string) => api.teams.removeMember(teamId, userId),
    onSuccess: invalidateTeam,
  });

  const profile = useQuery({ queryKey: ["team", teamId, "profile"], queryFn: () => api.teams.profile(teamId) });
  const status = useQuery({ queryKey: ["team", teamId, "status"], queryFn: () => api.teams.diagnosticStatus(teamId) });
  const gaps = useQuery({ queryKey: ["team", teamId, "gaps"], queryFn: () => api.teams.gapAnalysis(teamId) });

  const invite = useMutation({
    mutationFn: () => api.teams.invite(teamId),
    onSuccess: (data) => setInviteUrl(`${window.location.origin}/convite/${data.invite_token}`),
  });

  const createJob = useMutation({
    mutationFn: () => api.jobs.create({ title: jobTitle.trim(), team_id: teamId }),
    onSuccess: () => {
      setJobTitle("");
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  if (profile.isPending) return <Spinner />;
  if (profile.isError) return <ErrorState error={profile.error} onRetry={() => profile.refetch()} />;

  const team = profile.data;
  const traitData = Object.entries(team.trait_scores)
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value);

  const statusByDimension = new Map(gaps.data?.dimensions.map((d) => [d.dimension, d.status]) ?? []);
  const dimensionData = Object.entries(team.dimension_scores)
    .map(([label, value]) => ({ label, value, status: statusByDimension.get(label) }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="space-y-6">
      <PageTitle
        title={team.team_name}
        subtitle="Etapa 1 e 2 — diagnóstico do time e perfil-alvo por lacuna. Você é o responsável, não integrante."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" onClick={() => invite.mutate()} disabled={invite.isPending}>
              {invite.isPending ? "Gerando…" : "Gerar convite"}
            </Button>
            <ConfirmButton
              label="Excluir time"
              confirmLabel="Excluir o time e suas vagas?"
              disabled={removeTeam.isPending}
              onConfirm={() => removeTeam.mutate()}
            />
          </div>
        }
      />

      {inviteUrl && (
        <Callout tone="good" title="Convite gerado">
          <p className="mb-2">Envie este link aos integrantes. Ele expira em 30 dias.</p>
          <div className="flex flex-wrap items-center gap-2">
            <code
              className="rounded px-2 py-1 text-xs break-all"
              style={{ background: "var(--page-plane)", color: "var(--text-primary)" }}
            >
              {inviteUrl}
            </code>
            <Button variant="secondary" onClick={() => void navigator.clipboard.writeText(inviteUrl)}>
              Copiar
            </Button>
          </div>
        </Callout>
      )}

      {team.member_count === 0 ? (
        <Callout tone="info" title="O time ainda está vazio">
          Você é o <strong>responsável</strong> por este time, não um integrante — não precisa
          responder o teste, e suas respostas não entrariam na média. Gere o convite acima e envie a
          quem faz parte do time; o diagnóstico se forma conforme as pessoas respondem.
        </Callout>
      ) : (
        team.confidence_note && (
          <Callout tone={team.respondent_count === 0 ? "critical" : "warning"} title="Confiabilidade do diagnóstico">
            {team.confidence_note}
          </Callout>
        )
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <StatTile
          label="Integrantes"
          value={String(team.member_count)}
          hint={`${team.respondent_count} responderam o teste`}
        />
        <StatTile
          label="Diagnóstico completo"
          value={`${Math.round(team.completion_rate * 100)}%`}
          meter={team.completion_rate * 100}
          hint={status.data?.ready_for_job_opening ? "Maduro para abrir vaga." : "Poucos respondentes ainda."}
        />
        <StatTile
          label="Dispersão do perfil"
          value={team.dispersion.toFixed(2)}
          hint="Alta = time especializado, com lacunas nítidas. Baixa = perfil uniforme."
        >
          <InfoTip term="dispersão" />
        </StatTile>
      </div>

      {team.respondent_count > 0 && (
        <Radar
          title="Radar comportamental do time"
          subtitle="A forma média das 10 competências — os vales são as lacunas que uma contratação pode cobrir."
          series={[{ label: team.team_name, color: "var(--series-1)", scores: team.dimension_scores }]}
        />
      )}

      <Disclosure summary="Ver o perfil detalhado e o perfil-alvo por lacuna">
        <ProfileBars
          title="Perfil comportamental do time"
          subtitle="Competências derivadas dos fatores. ▼ lacuna · ▲ força — posições dentro deste time, não notas absolutas."
          data={dimensionData}
          emptyMessage="Ninguém do time respondeu o teste ainda."
        />

        <ProfileBars
          title="Fatores Big Five do time"
          subtitle="A camada latente medida diretamente pelo teste situacional."
          data={traitData}
          color="var(--series-2)"
          emptyMessage="Sem respostas ainda."
        />

        {/* ---------------------------------------------------- perfil-alvo */}
        {gaps.isSuccess && (
          <Card>
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            Perfil-alvo por lacuna
          </h3>
          <p className="mt-1 mb-4 text-sm" style={{ color: "var(--text-secondary)" }}>
            {gaps.data.summary}
          </p>

          {gaps.data.respondent_count > 0 && (
            <ul className="space-y-2">
              {gaps.data.dimensions
                .filter((dimension) => dimension.weight > 0)
                .map((dimension) => (
                  <li
                    key={dimension.dimension}
                    className="rounded-lg p-3"
                    style={{ border: "1px solid var(--hairline)" }}
                  >
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="flex items-center gap-1.5 text-sm font-medium">
                        <span aria-hidden style={{ color: DIMENSION_STATUS_COLOR[dimension.status] }}>
                          {DIMENSION_STATUS_ICON[dimension.status]}
                        </span>
                        {dimension.dimension}
                        <span className="text-xs font-normal" style={{ color: "var(--text-muted)" }}>
                          {DIMENSION_STATUS_LABEL[dimension.status]}
                        </span>
                      </span>
                      <span className="tabular text-sm" style={{ color: "var(--text-secondary)" }}>
                        peso {(dimension.weight * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div
                      className="mt-2 h-1.5 overflow-hidden rounded-full"
                      style={{ background: "color-mix(in srgb, var(--seq-fill) 22%, transparent)" }}
                    >
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${dimension.weight * 100}%`, background: "var(--seq-fill)" }}
                      />
                    </div>
                    <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
                      {dimension.rationale}
                    </p>
                  </li>
                ))}
            </ul>
          )}
        </Card>
        )}
      </Disclosure>

      {/* ------------------------------------------------- quem respondeu */}
      {status.isSuccess && (
        <Card>
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            Quem já respondeu
          </h3>
          <p className="mt-1 mb-3 text-xs" style={{ color: "var(--text-muted)" }}>
            Só integrantes entram nesta lista. Quem administra o time não aparece porque não compõe
            o diagnóstico.
          </p>
          {status.data.members.length === 0 && (
            <p className="py-4 text-center text-sm" style={{ color: "var(--text-muted)" }}>
              Ninguém entrou pelo convite ainda.
            </p>
          )}
          <ul className="divide-y" style={{ borderColor: "var(--gridline)" }}>
            {status.data.members.map((member) => (
              <li key={member.user_id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                <div>
                  <p className="text-sm" style={{ color: "var(--text-primary)" }}>
                    {member.name}
                    {member.is_owner && (
                      <span className="ml-2 text-xs" style={{ color: "var(--text-muted)" }}>
                        responsável
                      </span>
                    )}
                  </p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {member.email}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className="tabular text-xs"
                    style={{
                      color: member.assessment_completed ? "var(--status-good)" : "var(--text-muted)",
                    }}
                  >
                    <span aria-hidden>{member.assessment_completed ? "▲ " : "▼ "}</span>
                    {member.answered_questions}/{member.total_questions} cenários
                  </span>
                  {!member.is_owner && (
                    <ConfirmButton
                      label="Remover"
                      confirmLabel="Remover do time?"
                      disabled={removeMember.isPending}
                      onConfirm={() => removeMember.mutate(member.user_id)}
                    />
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* ------------------------------------------------------ nova vaga */}
      <Card>
        <h3 className="mb-3 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          Abrir vaga para este time
        </h3>
        {!status.data?.ready_for_job_opening && (
          <Callout tone="warning" title="Diagnóstico ainda imaturo">
            Com poucos respondentes o perfil-alvo tem margem de erro alta. Dá para abrir a vaga, mas
            o ranking sai frágil.
          </Callout>
        )}
        <form
          className="mt-3 flex flex-wrap items-end gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (jobTitle.trim()) createJob.mutate();
          }}
        >
          <div className="min-w-56 flex-1">
            <label htmlFor="job-title" className="mb-1.5 block text-sm font-medium">
              Título da vaga
            </label>
            <Input
              id="job-title"
              value={jobTitle}
              onChange={(event) => setJobTitle(event.target.value)}
              placeholder="ex.: Pessoa Desenvolvedora Backend Pleno"
            />
          </div>
          <Button type="submit" disabled={!jobTitle.trim() || createJob.isPending}>
            {createJob.isPending ? "Abrindo…" : "Abrir vaga"}
          </Button>
        </form>
        {createJob.isSuccess && (
          <div className="mt-3">
            <p className="mb-2 text-sm" style={{ color: "var(--text-secondary)" }}>
              Vaga criada.
            </p>
            <Link to={`/vagas/${createJob.data.id}`}>
              <Button variant="secondary">Ir para a vaga</Button>
            </Link>
          </div>
        )}
        {createJob.isError && (
          <p className="mt-3 text-sm" style={{ color: "var(--status-critical)" }}>
            {createJob.error instanceof Error ? createJob.error.message : "Erro ao abrir vaga."}
          </p>
        )}
      </Card>
    </div>
  );
}
