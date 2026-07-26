import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router";

import logoDark from "../assets/brand/logo.png";
import logoLight from "../assets/brand/logo-light.png";
import { useAuth } from "../auth/AuthContext";

const THEME_KEY = "matchrecruiter.theme";
type Theme = "light" | "dark" | "system";

function useTheme() {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem(THEME_KEY) as Theme | null) ?? "system",
  );
  const [systemPrefersDark, setSystemPrefersDark] = useState(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches,
  );

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  // Só a preferência salva não basta pra escolher a logo certa: no modo
  // "Sistema" precisa saber o tema JÁ RESOLVIDO, não só o rótulo guardado.
  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (event: MediaQueryListEvent) => setSystemPrefersDark(event.matches);
    query.addEventListener("change", handler);
    return () => query.removeEventListener("change", handler);
  }, []);

  const resolvedTheme: "light" | "dark" = theme === "system" ? (systemPrefersDark ? "dark" : "light") : theme;

  return { theme, setTheme, resolvedTheme };
}

/**
 * O modo de demonstração (sem Google real) exibe "Test User <sufixo>" — vem
 * fixo do backend mock (`security.py`), não é editável por aqui. Some só da
 * exibição: nome e sobrenome digitados continuam intactos.
 */
function displayName(name: string): string {
  return name.replace(/^Test User\s+/i, "").trim() || name;
}

/** Rótulo visível no header: só o primeiro nome. O avatar continua usando o
 *  nome completo pras iniciais — só o texto ao lado fica curto. */
function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] ?? name;
}

/** Iniciais para o avatar de fallback: primeira + última palavra do nome. */
function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** Foto do Google quando existe; senão um círculo com as iniciais do nome. */
function UserAvatar({ name, avatarUrl }: { name: string; avatarUrl: string | null }) {
  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt=""
        referrerPolicy="no-referrer"
        className="h-8 w-8 shrink-0 rounded-full object-cover"
        style={{ boxShadow: "0 0 0 2px rgba(255,255,255,0.15)" }}
      />
    );
  }
  return (
    <span
      aria-hidden
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold"
      style={{ background: "var(--brand-green)", color: "var(--brand-void)" }}
    >
      {initials(name)}
    </span>
  );
}

/** Ícone hamburguer/×, um só SVG que troca de forma pelo estado. */
function MenuIcon({ open }: { open: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
      {open ? (
        <path d="M5 5L15 15M15 5L5 15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      ) : (
        <path d="M3 6h14M3 10h14M3 14h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      )}
    </svg>
  );
}

export function Layout() {
  const { user, avatarUrl, logout } = useAuth();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const name = user ? displayName(user.name) : "";
  const logo = resolvedTheme === "dark" ? logoDark : logoLight;

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-3 py-1.5 text-sm transition-colors ${
      isActive ? "font-medium" : "hover:bg-black/5 dark:hover:bg-white/5"
    }`;

  // Versão do link pro painel mobile: bloco cheio, alvo de toque maior.
  const mobileLinkClass = ({ isActive }: { isActive: boolean }) =>
    `block rounded-lg px-3 py-2.5 text-sm transition-colors ${
      isActive ? "font-medium" : "hover:bg-black/5 dark:hover:bg-white/5"
    }`;

  // --seq-track/--text-primary já são a paleta de marca (ver index.css): no
  // claro isso pinta o item ativo de lilás-sobre-branco, no escuro de
  // roxo-sobre-void — o mesmo par de tokens resolve os dois temas.
  const activeStyle = ({ isActive }: { isActive: boolean }) => ({
    background: isActive ? "var(--seq-track)" : undefined,
    color: isActive ? "var(--text-primary)" : undefined,
  });

  // As duas abaixo são funções de render, e não componentes. Declaradas aqui
  // dentro, seriam recriadas a cada render do Layout e o React trataria cada
  // versão como um tipo novo — desmontando e remontando a subárvore (o
  // <select> de tema perderia o foco, os NavLink piscariam). Chamadas como
  // função, o JSX entra inline e nada remonta.

  // A navegação segue o papel: candidato não tem time nem vaga para
  // administrar, e os links levariam direto a um 403. O recrutador administra
  // o diagnóstico sem responder a ele — mostrar "Meu teste" pra ele só
  // criaria expectativa falsa.
  function renderNavItems({ mobile = false }: { mobile?: boolean } = {}) {
    const cls = mobile ? mobileLinkClass : linkClass;
    const onClick = mobile ? () => setMenuOpen(false) : undefined;
    return (
      <>
        {user?.role === "RECRUITER" && (
          <>
            <NavLink to="/" end className={cls} style={activeStyle} onClick={onClick}>
              Times
            </NavLink>
            <NavLink to="/vagas" className={cls} style={activeStyle} onClick={onClick}>
              Vagas
            </NavLink>
            <NavLink to="/candidatos" className={cls} style={activeStyle} onClick={onClick}>
              Candidatos
            </NavLink>
          </>
        )}
        {user?.role === "MEMBER" && (
          <NavLink to="/meu-teste" className={cls} style={activeStyle} onClick={onClick}>
            Meu teste
          </NavLink>
        )}
      </>
    );
  }

  function renderThemeSelect() {
    return (
      <>
        <label className="sr-only" htmlFor="theme">
          Tema
        </label>
        <select
          id="theme"
          value={theme}
          onChange={(event) => setTheme(event.target.value as Theme)}
          className="rounded-lg px-2 py-1.5 text-xs outline-none"
          style={{ background: "var(--page-plane)", color: "var(--text-secondary)", border: "1px solid var(--hairline)" }}
        >
          <option value="system">Tema do sistema</option>
          <option value="light">Claro</option>
          <option value="dark">Escuro</option>
        </select>
      </>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--page-plane)", color: "var(--text-primary)" }}>
      <header
        className="sticky top-0 z-20 backdrop-blur"
        style={{ background: "var(--surface-1)", borderBottom: "1px solid var(--hairline)" }}
      >
        {/* Abaixo de lg (mobile e tablet): logo + botão de menu, nada mais no
            header — nav, tema, avatar e sair vivem no painel. Em lg+: a
            grade de 3 colunas de sempre, tudo inline. */}
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:grid lg:grid-cols-[1fr_auto_1fr]">
          <NavLink to="/" className="flex items-center justify-self-start" onClick={() => setMenuOpen(false)}>
            <img src={logo} alt="MatchRecruiter" className="h-6 w-auto" />
          </NavLink>

          {user ? (
            <nav className="hidden items-center gap-1 justify-self-center lg:flex" style={{ color: "var(--text-secondary)" }}>
              {renderNavItems()}
            </nav>
          ) : (
            <span className="hidden lg:block" />
          )}

          <div className="hidden items-center gap-3 justify-self-end lg:flex">
            {renderThemeSelect()}
            {user && (
              <div className="flex items-center gap-2.5">
                <UserAvatar name={name} avatarUrl={avatarUrl} />
                <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {firstName(name)}
                </span>
                <button
                  type="button"
                  onClick={logout}
                  className="rounded-lg px-3 py-1.5 text-sm transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                  style={{ color: "var(--text-secondary)" }}
                >
                  Sair
                </button>
              </div>
            )}
          </div>

          {user && (
            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              aria-expanded={menuOpen}
              aria-controls="mobile-menu"
              aria-label={menuOpen ? "Fechar menu" : "Abrir menu"}
              className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-black/5 dark:hover:bg-white/5 lg:hidden"
              style={{ color: "var(--text-primary)" }}
            >
              <MenuIcon open={menuOpen} />
            </button>
          )}
        </div>

        {/* Painel do menu — mobile e tablet (abaixo de lg). Reúne o que some
            do header nesses tamanhos: identidade, navegação e tema. */}
        {user && menuOpen && (
          <div id="mobile-menu" className="lg:hidden" style={{ borderTop: "1px solid var(--hairline)" }}>
            <div className="mx-auto max-w-6xl px-4 py-3 sm:px-6">
              <div className="flex items-center gap-3 pb-3" style={{ borderBottom: "1px solid var(--hairline)" }}>
                <UserAvatar name={name} avatarUrl={avatarUrl} />
                <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {firstName(name)}
                </span>
              </div>

              <nav className="flex flex-col gap-0.5 py-3" style={{ color: "var(--text-secondary)" }}>
                {renderNavItems({ mobile: true })}
              </nav>

              <div className="flex items-center justify-between gap-3 pt-3" style={{ borderTop: "1px solid var(--hairline)" }}>
                {renderThemeSelect()}
                <button
                  type="button"
                  onClick={() => {
                    logout();
                    setMenuOpen(false);
                  }}
                  className="rounded-lg px-3 py-1.5 text-sm transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                  style={{ color: "var(--text-secondary)" }}
                >
                  Sair
                </button>
              </div>
            </div>
          </div>
        )}
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  );
}
