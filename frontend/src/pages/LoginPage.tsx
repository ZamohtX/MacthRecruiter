import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { GOOGLE_CLIENT_ID, MOCK_MODE, useAuth } from "../auth/AuthContext";

import "./landing.css";

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

/** Logo: o "M" branco com o chevron verde da marca. */
function Mark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true">
      <path className="mark-letter" d="M2 21V5l7.5 8L17 5v16" fill="none" strokeWidth="2.6" strokeLinejoin="round" />
      <path className="mark-chevron" d="M17 13l7-8v16l-7-8z" />
    </svg>
  );
}

/**
 * Radar da lacuna: o time (tracejado) afunda em Extroversão e a candidata
 * (verde) avança exatamente ali. É a tese do produto em uma imagem — por isso
 * ocupa o lugar que normalmente seria de um número grande com gradiente.
 */
function GapRadar() {
  return (
    <svg viewBox="0 0 300 300" role="img" aria-labelledby="radar-titulo radar-desc">
      <title id="radar-titulo">Perfil do time e do candidato nos cinco fatores</title>
      <desc id="radar-desc">
        O time pontua alto em quatro fatores e baixo em Extroversão. O candidato tem o formato
        inverso: cobre exatamente o fator em que o time é mais fraco.
      </desc>

      <g className="radar-grid" fill="none" strokeWidth="1">
        <polygon points="150,40 254.6,116 214.7,239 85.3,239 45.4,116" />
        <polygon points="150,67.5 228.4,124.5 198.5,216.7 101.5,216.7 71.6,124.5" />
        <polygon points="150,95 202.3,133 182.3,194.5 117.7,194.5 97.7,133" />
        <polygon points="150,122.5 176.2,141.5 166.2,172.2 133.8,172.2 123.8,141.5" />
        <path d="M150 150L150 40M150 150L254.6 116M150 150L214.7 239M150 150L85.3 239M150 150L45.4 116" />
      </g>

      <polygon
        className="poly-team"
        points="150,59.8 231.6,123.5 172.6,181.1 102.1,215.9 66.3,122.8"
        strokeWidth="2"
        strokeDasharray="5 4"
      />
      <polygon
        className="poly-cand"
        points="150,100.5 204.4,132.3 206.9,228.3 119,192.7 92.5,131.3"
        strokeWidth="2.4"
      />

      <g className="gap-mark">
        <circle cx="172.6" cy="181.1" r="16" fill="none" strokeWidth="1.5" />
      </g>
      <circle className="gap-dot" cx="172.6" cy="181.1" r="4" />

      <g className="radar-label" fontFamily="Instrument Sans, sans-serif" fontSize="10.5" textAnchor="middle">
        <text x="150" y="28">
          Abertura
        </text>
        <text x="268" y="112">
          Consciência
        </text>
        <text x="222" y="256">
          Extroversão
        </text>
        <text x="78" y="256">
          Amabilidade
        </text>
        <text x="32" y="112">
          Estabilidade
        </text>
      </g>
    </svg>
  );
}

export function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [suffix, setSuffix] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // O botão do Google aparece em dois lugares (topo e cartão de entrada), e o
  // GIS precisa de um nó por instância.
  const navButtonRef = useRef<HTMLDivElement>(null);
  const cardButtonRef = useRef<HTMLDivElement>(null);

  // O convite de time e o link de vaga chegam como query string e precisam
  // sobreviver ao login: são eles que vinculam a pessoa ao time ou à vaga.
  const inviteToken = searchParams.get("convite");
  const jobId = searchParams.get("vaga");
  const next = searchParams.get("next");

  // Quem chega por convite ou vaga veio responder o teste, não ler a
  // apresentação do produto: nesse caso a página é só o cartão de entrada.
  const focused = Boolean(inviteToken || jobId);

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

  // O callback do GIS é registrado uma vez só e sobreviveria com uma versão
  // velha de `submit` — a ref mantém a atual sem re-inicializar o script.
  // A atribuição vai num efeito, não no corpo do render: sob render
  // concorrente o React pode descartar um render, e a ref já teria mudado.
  const submitRef = useRef(submit);
  useEffect(() => {
    submitRef.current = submit;
  });

  // Google Identity Services só é carregado quando há client ID configurado.
  useEffect(() => {
    if (MOCK_MODE) return;

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => {
      if (!window.google) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (response) => void submitRef.current(response.credential),
      });
      for (const slot of [navButtonRef.current, cardButtonRef.current]) {
        if (!slot) continue;
        window.google.accounts.id.renderButton(slot, {
          theme: "outline",
          size: "large",
          shape: "pill",
          text: "continue_with",
          locale: "pt-BR",
        });
      }
    };
    document.head.append(script);

    return () => script.remove();
  }, [focused]);

  const cleanSuffix = suffix.trim().toLowerCase().replace(/[^a-z0-9]/g, "") || "demo";

  const signIn = (
    <div className="signin" id="entrar">
      {!focused && (
        <>
          <p className="eyebrow">Entrar</p>
          <h2 style={{ marginTop: "0.8rem" }}>Comece pelo time que você já tem.</h2>
          <p className="lede" style={{ marginTop: "1.1rem" }}>
            O diagnóstico leva 12 minutos por pessoa e não exige nenhuma vaga aberta.
          </p>
        </>
      )}

      {focused && (
        <>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: "1.5rem" }}>
            <Mark size={40} />
          </div>
          <h2>{inviteToken ? "Você foi convidado" : "Candidatura"}</h2>
          <p className="lede" style={{ marginTop: "1rem" }}>
            {inviteToken
              ? "Entre para responder o diagnóstico comportamental do seu time."
              : "Entre para se candidatar e responder o teste da vaga."}
          </p>
        </>
      )}

      <div className="signin-card">
        {MOCK_MODE ? (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void submit(`mock_google_token_${cleanSuffix}`);
            }}
          >
            <p className="demo-note">
              <strong>Modo de demonstração</strong>
              Sem <code>VITE_GOOGLE_CLIENT_ID</code> configurado, o login usa os tokens simulados do
              backend. O mesmo texto entra sempre na mesma conta, então dá para simular time e
              candidatos em abas diferentes.
            </p>

            <label className="field-label" htmlFor="suffix">
              Identificador
            </label>
            <input
              id="suffix"
              className="field"
              value={suffix}
              onChange={(event) => setSuffix(event.target.value)}
              placeholder="ex.: ana, recrutador, membro1"
              autoFocus={focused}
            />
            <p className="hint">
              Vira <code>mock_google_token_{cleanSuffix}</code>
            </p>

            <button type="submit" className="btn btn-primary" style={{ width: "100%", marginTop: "1.2rem" }} disabled={busy}>
              {busy ? "Entrando…" : "Entrar"}
            </button>
          </form>
        ) : (
          <>
            <p style={{ color: "var(--lilac)", fontSize: "0.92rem", marginBottom: "1.2rem" }}>
              Use sua conta Google corporativa.
            </p>
            <div className="gsi-slot" ref={cardButtonRef} />
            {busy && <p className="hint" style={{ textAlign: "center" }}>Entrando…</p>}
          </>
        )}

        {error && <p className="error">{error}</p>}
      </div>

      {/* Na landing completa a ressalva já está no rodapé; repetir aqui seria
          dizer a mesma coisa duas vezes na mesma rolagem. */}
      {focused && (
        <p className="disclaimer" style={{ marginTop: "1.5rem", fontSize: "0.82rem", color: "var(--lilac-dim)" }}>
          O teste comportamental aplicado aqui é uma proposta de produto, não um instrumento
          psicometricamente validado. Os resultados apoiam a decisão do recrutador — não a
          substituem.
        </p>
      )}
    </div>
  );

  if (focused) {
    return <div className="mr-landing is-focused">{signIn}</div>;
  }

  return (
    <div className="mr-landing">
      <div className="shell">
        <nav className="nav">
          <a className="brand" href="#topo">
            <Mark />
            MatchRecruit
          </a>
          <div className="nav-links">
            <a href="#metodo">Método</a>
            <a href="#como">Como funciona</a>
            {MOCK_MODE ? (
              <a className="btn btn-primary" href="#entrar">
                Entrar
              </a>
            ) : (
              <div className="gsi-slot" ref={navButtonRef} />
            )}
          </div>
        </nav>
      </div>

      <header className="shell hero" id="topo">
        <span className="tag">
          <span className="dot" /> Diagnóstico do time antes da vaga abrir
        </span>

        <h1>
          Contrate pela <em>lacuna</em>, não pela semelhança.
        </h1>

        <p className="lede">
          Times criativos contratam mais criativos. Times analíticos contratam mais analíticos. O
          resultado é uma equipe maior, não melhor. O MatchRecruit mede a diferença — e ranqueia por
          ela.
        </p>

        <div className="hero-actions">
          <a className="btn btn-primary" href="#entrar">
            Começar o diagnóstico
          </a>
          <a className="btn btn-ghost" href="#como">
            Ver como funciona
          </a>
        </div>

        <p className="hero-note">20 situações de trabalho. Sem resposta certa. 12 minutos.</p>

        <div className="signature">
          <figure>
            <GapRadar />
          </figure>

          <div className="legend">
            <p className="eyebrow">Vaga de Analista de Dados · time de 6 pessoas</p>

            <div className="legend-row">
              <span className="swatch swatch-team" />
              <span>
                <strong>O time hoje</strong>
                Forte em quatro fatores, fraco em Extroversão. A lacuna não aparece em currículo
                nenhum.
              </span>
            </div>

            <div className="legend-row">
              <span className="swatch swatch-cand" />
              <span>
                <strong>Candidata Marina</strong>
                O formato inverso. Não é a pessoa mais parecida com o time — é a que completa o que
                falta.
              </span>
            </div>

            <div className="verdict">
              <b>+18</b>
              <span>
                pontos na média do time em Extroversão, se ela entrar. Simulado antes da
                contratação.
              </span>
            </div>
          </div>
        </div>
      </header>

      <section id="metodo" className="shell">
        <div className="section-head">
          <p className="eyebrow">O que o mercado trata como uma coisa só</p>
          <h2>Dois tipos de fit. Só um deles faz o time melhor.</h2>
          <p className="lede">
            Quase toda ferramenta de recrutamento mede semelhança e chama isso de fit cultural. Nós
            separamos os dois, e mostramos os dois.
          </p>
        </div>

        <div className="split">
          <article className="panel panel-lead">
            <h3>Fit complementar</h3>
            <p>
              O quanto a pessoa cobre o que falta na equipe. É o que ordena a lista de candidatos —
              porque é o que muda a capacidade do time.
            </p>
          </article>

          <article className="panel">
            <h3>Fit suplementar</h3>
            <p>
              O quanto a pessoa se parece com quem já está lá. Aparece no painel, mas não ranqueia:
              em excesso, é o nome técnico para contratar mais do mesmo.
            </p>
          </article>

          <article className="panel">
            <h3>Simulação pós-contratação</h3>
            <p>
              Antes de decidir, a plataforma recalcula a média do time como se aquela pessoa já
              tivesse entrado. A decisão deixa de ser sobre o candidato isolado.
            </p>
          </article>
        </div>
      </section>

      <div className="shell">
        <div className="band">
          <div>
            <b>20</b>
            <span>situações de trabalho, com 4 condutas defensáveis em cada</span>
          </div>
          <div>
            <b>5</b>
            <span>fatores do Big Five, o modelo de personalidade com maior base empírica</span>
          </div>
          <div>
            <b>10</b>
            <span>soft skills derivadas dos fatores, sem pergunta autodeclarada</span>
          </div>
        </div>
      </div>

      <section id="como" className="shell">
        <div className="section-head">
          <p className="eyebrow">Como funciona</p>
          <h2>A ordem é o método.</h2>
          <p className="lede">
            O time responde <em>antes</em> de a vaga existir. Inverter isso é como escolher o
            remédio antes do diagnóstico.
          </p>
        </div>

        <div className="steps">
          <article className="step">
            <h3>A equipe atual responde</h3>
            <p>
              Cada integrante faz o teste de julgamento situacional. Sai o perfil coletivo — e onde
              ele afunda.
            </p>
          </article>

          <article className="step">
            <h3>A vaga nasce da lacuna</h3>
            <p>
              O perfil-alvo não é escrito por intuição: é derivado da diferença entre o time que
              existe e o que ele precisa ter.
            </p>
          </article>

          <article className="step">
            <h3>O candidato faz o mesmo teste</h3>
            <p>
              Mesmo instrumento, mesma escala. Comparação direta, sem tradução entre dois
              questionários diferentes.
            </p>
          </article>

          <article className="step">
            <h3>Você vê o time depois dele</h3>
            <p>
              O ranking mostra quem fecha a lacuna, e a simulação mostra o time resultante. Aí se
              contrata.
            </p>
          </article>
        </div>
      </section>

      <section className="shell closer">{signIn}</section>

      <div className="shell">
        <footer>
          <span>© 2026 MatchRecruit · Conecta. Avalia. Contrata.</span>
          <p className="disclaimer">
            O instrumento é uma proposta de produto, ancorada em Big Five, e não uma medida
            psicometricamente validada: as cargas dos fatores foram definidas por julgamento
            informado pela literatura, não estimadas a partir de dados.
          </p>
        </footer>
      </div>
    </div>
  );
}
