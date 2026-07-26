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

const AVATAR_KEY = "matchrecruiter.avatar";

/**
 * O backend não guarda a foto do Google — só `google_id`. O `id_token` que o
 * Google entrega é, ele mesmo, um JWT com a claim `picture`; decodificar o
 * payload no navegador (sem verificar assinatura, que já é validada pelo
 * backend em `/auth/google`) extrai a foto sem precisar de coluna nova.
 * Token mock (`mock_google_token_<sufixo>`) não é um JWT — cai no `null`.
 */
function decodeGooglePicture(idToken: string): string | null {
  const parts = idToken.split(".");
  if (parts.length !== 3) return null;
  try {
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.picture === "string" ? payload.picture : null;
  } catch {
    return null;
  }
}

export interface LoginOptions {
  inviteToken?: string | null;
  jobId?: string | null;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  /** Foto de perfil do Google, quando o login veio de lá. `null` em modo mock. */
  avatarUrl: string | null;
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
  // Persistida à parte do token de acesso: o `access_token` emitido pelo
  // backend não carrega a claim `picture`, só o id_token original do Google a
  // tinha — sem isso, a foto sumiria a cada F5.
  const [avatarUrl, setAvatarUrl] = useState<string | null>(() => localStorage.getItem(AVATAR_KEY));

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

    const picture = decodeGooglePicture(idToken);
    if (picture) localStorage.setItem(AVATAR_KEY, picture);
    else localStorage.removeItem(AVATAR_KEY);
    setAvatarUrl(picture);

    return response.user;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(AVATAR_KEY);
    setAvatarUrl(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, avatarUrl, login, logout }),
    [user, loading, avatarUrl, login, logout],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth(): AuthState {
  const context = use(AuthContext);
  if (!context) throw new Error("useAuth precisa estar dentro de <AuthProvider>");
  return context;
}
