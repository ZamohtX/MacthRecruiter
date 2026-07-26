import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";

import { api } from "../api/client";
import { Button, Card, ConfirmButton, EmptyState, ErrorState, Input, PageTitle, Spinner } from "../components/ui";

export function TeamsPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");

  const teams = useQuery({ queryKey: ["teams"], queryFn: api.teams.list });

  const create = useMutation({
    mutationFn: api.teams.create,
    onSuccess: () => {
      setName("");
      void queryClient.invalidateQueries({ queryKey: ["teams"] });
    },
  });

  const removeTeam = useMutation({
    mutationFn: (teamId: string) => api.teams.remove(teamId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["teams"] }),
  });

  return (
    <div>
      <PageTitle
        title="Times"
        subtitle="O diagnóstico do time vem antes da vaga — é ele que define o perfil-alvo."
      />

      <Card className="mb-6">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (name.trim()) create.mutate(name.trim());
          }}
        >
          <div className="min-w-56 flex-1">
            <label htmlFor="team-name" className="mb-1.5 block text-sm font-medium">
              Novo time
            </label>
            <Input
              id="team-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="ex.: Squad de Plataforma"
            />
          </div>
          <Button type="submit" disabled={!name.trim() || create.isPending}>
            {create.isPending ? "Criando…" : "Criar time"}
          </Button>
        </form>
        {create.isError && (
          <p className="mt-3 text-sm" style={{ color: "var(--status-critical)" }}>
            {create.error instanceof Error ? create.error.message : "Erro ao criar."}
          </p>
        )}
        <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
          As melhores contratações começam entendendo quem já faz parte da equipe.
        </p>
      </Card>

      {teams.isPending && <Spinner />}
      {teams.isError && <ErrorState error={teams.error} onRetry={() => teams.refetch()} />}

      {teams.isSuccess &&
        (teams.data.length === 0 ? (
          <EmptyState
            title="Nenhum time ainda"
            description="Crie um time acima, convide os integrantes e aplique o diagnóstico comportamental antes de abrir a vaga."
          />
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {teams.data.map((team) => (
              <li
                key={team.id}
                className="flex items-center justify-between gap-3 rounded-xl p-4"
                style={{ background: "var(--surface-1)", border: "1px solid var(--hairline)" }}
              >
                <Link to={`/times/${team.id}`} className="min-w-0 flex-1">
                  <p className="truncate font-medium" style={{ color: "var(--text-primary)" }}>
                    {team.name}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                    Criado em {new Date(team.created_at).toLocaleDateString("pt-BR")}
                  </p>
                </Link>
                <ConfirmButton
                  label="Excluir"
                  confirmLabel="Excluir o time?"
                  disabled={removeTeam.isPending}
                  onConfirm={() => removeTeam.mutate(team.id)}
                />
              </li>
            ))}
          </ul>
        ))}
    </div>
  );
}
