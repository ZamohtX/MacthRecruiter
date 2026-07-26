import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { GOOGLE_CLIENT_ID, MOCK_MODE, useAuth } from "../auth/AuthContext";
import { Button, Callout, Card, Input } from "../components/ui";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (r: { credential: string }) => void }) => void;
          renderButton: (el: HTMLElement, options: Record<string, unknown>) => void;
        };
      };
    };
  }
}

export function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [suffix, setSuffix] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const googleButtonRef = useRef<HTMLDivElement>(null);

  // O convite de time e o link de vaga chegam como query string e precisam
  // sobreviver ao login: são eles que vinculam a pessoa ao time ou à vaga.
  const inviteToken = searchParams.get("convite");
  const jobId = searchParams.get("vaga");
  const next = searchParams.get("next");

  useEffect(() => {
    if (user) navigate(next ?? "/", { replace: true });
  }, [user, navigate, next]);

  async function submit(idToken: string) {
    setBusy(true);
    setError(null);
    try {
      await login(idToken, { inviteToken, jobId });
      navigate(next ?? "/", { replace: true });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao entrar.");
    } finally {
      setBusy(false);
    }
  }

  // Google Identity Services só é carregado quando há client ID configurado.
  useEffect(() => {
    if (MOCK_MODE || !googleButtonRef.current) return;

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => {
      if (!window.google || !googleButtonRef.current) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (response) => void submit(response.credential),
      });
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: "outline",
        size: "large",
        text: "continue_with",
        locale: "pt-BR",
      });
    };
    document.head.append(script);

    return () => script.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto max-w-md py-12">
      <h1 className="text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
        Entrar
      </h1>
      <p className="mt-1 mb-6 text-sm" style={{ color: "var(--text-secondary)" }}>
        {inviteToken
          ? "Você foi convidado para responder o diagnóstico de um time."
          : jobId
            ? "Você está se candidatando a uma vaga."
            : "Acesse o diagnóstico do seu time e o painel de candidatos."}
      </p>

      <Card>
        {MOCK_MODE ? (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const clean = suffix.trim().toLowerCase().replace(/[^a-z0-9]/g, "") || "demo";
              void submit(`mock_google_token_${clean}`);
            }}
          >
            <Callout tone="info" title="Modo de demonstração">
              Sem <code>VITE_GOOGLE_CLIENT_ID</code> configurado, o login usa os tokens simulados do
              backend. Escolha um identificador: o mesmo texto entra sempre na mesma conta, então dá
              para simular time e candidatos em abas diferentes.
            </Callout>

            <label htmlFor="suffix" className="mt-4 mb-1.5 block text-sm font-medium">
              Identificador
            </label>
            <Input
              id="suffix"
              value={suffix}
              onChange={(event) => setSuffix(event.target.value)}
              placeholder="ex.: ana, recrutador, membro1"
              autoFocus
            />
            <p className="mt-1.5 text-xs" style={{ color: "var(--text-muted)" }}>
              Vira <code>mock_google_token_{suffix.trim().toLowerCase().replace(/[^a-z0-9]/g, "") || "demo"}</code>
            </p>

            <Button type="submit" className="mt-4 w-full" disabled={busy}>
              {busy ? "Entrando…" : "Entrar"}
            </Button>
          </form>
        ) : (
          <div>
            <p className="mb-4 text-sm" style={{ color: "var(--text-secondary)" }}>
              Use sua conta Google corporativa.
            </p>
            <div ref={googleButtonRef} />
            {busy && (
              <p className="mt-3 text-sm" style={{ color: "var(--text-muted)" }}>
                Entrando…
              </p>
            )}
          </div>
        )}

        {error && (
          <p className="mt-4 text-sm" style={{ color: "var(--status-critical)" }}>
            {error}
          </p>
        )}
      </Card>

      <p className="mt-6 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
        O teste comportamental aplicado aqui é uma proposta de produto, não um instrumento
        psicometricamente validado. Os resultados apoiam a decisão do recrutador — não a substituem.
      </p>
    </div>
  );
}
