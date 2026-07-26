import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router";

import { useAuth } from "../auth/AuthContext";
import { Button } from "./ui";

const THEME_KEY = "matchrecruiter.theme";
type Theme = "light" | "dark" | "system";

function useTheme() {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem(THEME_KEY) as Theme | null) ?? "system",
  );

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  return { theme, setTheme };
}

const ROLE_LABEL = {
  RECRUITER: "Recrutador",
  MEMBER: "Integrante do time",
  CANDIDATE: "Candidato",
} as const;

export function Layout() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-3 py-1.5 text-sm transition-colors ${
      isActive ? "bg-black/5 font-medium dark:bg-white/10" : "hover:bg-black/5 dark:hover:bg-white/10"
    }`;

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-10 backdrop-blur" style={{ borderBottom: "1px solid var(--hairline)" }}>
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-6 py-3">
          <NavLink to="/" className="flex items-baseline gap-2">
            <span className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
              MatchRecruiter
            </span>
            <span className="hidden text-xs sm:inline" style={{ color: "var(--text-muted)" }}>
              contratar por lacuna
            </span>
          </NavLink>

          {user && (
            // A navegação segue o papel: candidato não tem time nem vaga para
            // administrar, e os links levariam direto a um 403.
            <nav className="flex items-center gap-1" style={{ color: "var(--text-secondary)" }}>
              {user.role === "RECRUITER" && (
                <>
                  <NavLink to="/" className={linkClass} end>
                    Times
                  </NavLink>
                  <NavLink to="/vagas" className={linkClass}>
                    Vagas
                  </NavLink>
                </>
              )}
              {/* O recrutador administra o diagnóstico sem responder a ele:
                  não é integrante do time e suas respostas não entrariam na
                  média. Mostrar o link só criaria expectativa falsa. */}
              {user.role === "MEMBER" && (
                <NavLink to="/meu-teste" className={linkClass}>
                  Meu teste
                </NavLink>
              )}
            </nav>
          )}

          <div className="ml-auto flex items-center gap-3">
            <label className="sr-only" htmlFor="theme">
              Tema
            </label>
            <select
              id="theme"
              value={theme}
              onChange={(event) => setTheme(event.target.value as Theme)}
              className="rounded-lg px-2 py-1.5 text-xs outline-none"
              style={{
                background: "var(--surface-1)",
                color: "var(--text-secondary)",
                border: "1px solid var(--hairline)",
              }}
            >
              <option value="system">Tema do sistema</option>
              <option value="light">Claro</option>
              <option value="dark">Escuro</option>
            </select>

            {user && (
              <div className="flex items-center gap-3">
                <div className="hidden text-right sm:block">
                  <p className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                    {user.name}
                  </p>
                  <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                    {ROLE_LABEL[user.role]}
                  </p>
                </div>
                <Button variant="ghost" onClick={logout}>
                  Sair
                </Button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
