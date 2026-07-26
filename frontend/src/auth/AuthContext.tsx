import { createContext, use, useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { ApiError, api, getToken, setToken } from "../api/client";
import type { User } from "../api/types";

export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? "";

/**
 * Sem client ID configurado a aplicação entra em modo mock, que casa com o
 * `GOOGLE_CLIENT_ID=mock_google_client_id` do backend: qualquer token no
 * formato `mock_google_token_<sufixo>` cria e loga um usuário determinístico.
 * É isso que torna o fluxo inteiro demonstrável sem credenciais do Google.
 */
export const MOCK_MODE = GOOGLE_CLIENT_ID === "";

export interface LoginOptions {
  inviteToken?: string | null;
  jobId?: string | null;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  /** `idToken` é o token do Google, ou `mock_google_token_<sufixo>` em dev. */
  login: (idToken: string, options?: LoginOptions) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // Sem token guardado não há o que revalidar, então já nasce carregado. Derivar
  // aqui em vez de chamar setState no corpo do efeito evita um render em cascata
  // — e um piscar do spinner em toda visita anônima.
  const [loading, setLoading] = useState(() => getToken() !== null);

  // Revalida o token guardado na subida: um JWT expirado no localStorage
  // deixaria a UI achar que está logada e falhar em toda chamada.
  useEffect(() => {
    if (!getToken()) return;

    let active = true;

    api.auth
      .me()
      .then((me) => {
        if (active) setUser(me);
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) setToken(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (idToken: string, options: LoginOptions = {}) => {
    const response = await api.auth.google({
      id_token: idToken,
      invite_token: options.inviteToken ?? null,
      job_id: options.jobId ?? null,
    });
    setToken(response.access_token);
    setUser(response.user);
    return response.user;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout]);

  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth(): AuthState {
  const context = use(AuthContext);
  if (!context) throw new Error("useAuth precisa estar dentro de <AuthProvider>");
  return context;
}
