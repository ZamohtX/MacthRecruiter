import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import logo from "../assets/brand/logo.png";
import { GOOGLE_CLIENT_ID, MOCK_MODE, useAuth } from "../auth/AuthContext";

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

/**
 * Tela de marca, não a superfície neutra do resto do app: usa a paleta fixa
 * (--brand-*) em vez dos tokens --surface-1/--text-* que seguem o tema
 * claro/escuro do usuário. Um visitante não logado ainda não escolheu tema —
 * a primeira impressão é a marca, não uma preferência de sistema.
 */
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
        theme: "filled_black",
        size: "large",
        text: "continue_with",
        locale: "pt-BR",
      });
    };
    document.head.append(script);

    return () => script.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // O sufixo vira e-mail fake no backend mock (`user_<sufixo>@example.com`,
  // ver `security.py`) — espaço ali quebra o e-mail (500). Hífen é válido em
  // e-mail e continua marcando a fronteira entre nome e sobrenome pra exibir
  // só o primeiro nome depois (ver `firstName` em Layout.tsx).
  function sanitize(value: string): string {
    return value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");
  }

  const clean = sanitize(suffix);
  const canSubmit = clean.length > 0;

  return (
    <div
      className="flex min-h-screen items-center justify-center px-6 py-12"
      style={{
        background: "radial-gradient(120% 100% at 50% -10%, var(--brand-violet) 0%, var(--brand-void) 55%)",
      }}
    >
      <div className="w-full max-w-sm">
        <img src={logo} alt="MatchRecruiter — Conecte. Avalie. Contrate." className="mx-auto w-full max-w-[150px]" />

        <p className="mt-6 mb-8 text-center text-sm" style={{ color: "var(--brand-mist)" }}>
          {inviteToken
            ? "Você foi convidado para responder o diagnóstico de um time."
            : jobId
              ? "Você está se candidatando a uma vaga."
              : "Acesse o diagnóstico do seu time e o painel de candidatos."}
        </p>

        <div
          className="rounded-2xl p-6"
          style={{
            background: "color-mix(in srgb, var(--brand-void) 55%, var(--brand-violet) 20%)",
            border: "1px solid color-mix(in srgb, var(--brand-violet-light) 45%, transparent)",
          }}
        >
          {MOCK_MODE ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                if (!canSubmit) {
                  setError("Digite seu nome para continuar.");
                  return;
                }
                void submit(`mock_google_token_${clean}`);
              }}
            >
              <div className="rounded-lg p-3 text-xs leading-relaxed" style={{ background: "rgba(0,0,0,0.25)" }}>
                <p className="mb-1 flex items-center gap-1.5 font-medium text-white">
                  <span
                    aria-hidden
                    className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-bold"
                    style={{ background: "var(--brand-green)", color: "var(--brand-void)" }}
                  >
                    i
                  </span>
                  Modo de demonstração
                </p>
                <p style={{ color: "var(--brand-mist)" }}>
                  Sem <code className="rounded bg-white/10 px-1 py-0.5">VITE_GOOGLE_CLIENT_ID</code> configurado, o
                  login usa os tokens simulados do backend. Escolha um identificador: o mesmo texto entra sempre na
                  mesma conta, então dá para simular time e candidatos em abas diferentes.
                </p>
              </div>

              <label htmlFor="suffix" className="mt-4 mb-1.5 block text-sm font-medium" style={{ color: "var(--brand-mist)" }}>
                Antes de começar, identifique-se
              </label>
              <input
                id="suffix"
                value={suffix}
                onChange={(event) => {
                  setSuffix(event.target.value);
                  if (error) setError(null);
                }}
                placeholder="ex.: ana, recrutador, membro1"
                autoFocus
                aria-invalid={error ? true : undefined}
                className="w-full rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:ring-2 focus:ring-[var(--brand-green)] focus:ring-offset-2 focus:ring-offset-[var(--brand-void)]"
                style={{
                  background: "rgba(0,0,0,0.3)",
                  border: `1px solid ${error ? "#ff8080" : "rgba(255,255,255,0.14)"}`,
                }}
              />

              <button
                type="submit"
                disabled={busy || !canSubmit}
                className="group relative mt-5 flex w-full items-center gap-3 rounded-full p-1.5 pr-5 transition-transform active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 cursor-pointer"
                style={{ background: "linear-gradient(135deg, var(--brand-violet) 0%, var(--brand-violet-light) 100%)" }}
              >
                <span
                  className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full"
                  style={{ boxShadow: "0 0 0 2px rgba(255,255,255,0.14)" }}
                >
                  <img src="/android-chrome-192x192.png" alt="" className="h-full w-full object-cover" />
                </span>
                <span
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-full py-2 text-sm font-bold"
                  style={{ background: "var(--brand-green)", color: "var(--brand-void)" }}
                >
                  {busy ? "Entrando…" : "Entrar"}
                  {!busy && (
                    <svg width="12" height="8" viewBox="0 0 12 8" fill="none" aria-hidden>
                      <path d="M1 1.5L6 6.5L11 1.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </span>
              </button>
            </form>
          ) : (
            <div>
              <p className="mb-4 text-sm" style={{ color: "var(--brand-mist)" }}>
                Use sua conta Google corporativa.
              </p>
              <div ref={googleButtonRef} />
              {busy && (
                <p className="mt-3 text-sm" style={{ color: "var(--brand-mist)" }}>
                  Entrando…
                </p>
              )}
            </div>
          )}

          {error && (
            <p className="mt-4 text-sm font-medium" style={{ color: "#ff8080" }}>
              {error}
            </p>
          )}
        </div>

      
      </div>
    </div>
  );
}
