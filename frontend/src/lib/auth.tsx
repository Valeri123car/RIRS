"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { ApiError, apiRequest } from "@/lib/api";

export type User = { id: number; email: string; role: "player" | "coach" | "admin" };

type TokenResponse = { access_token: string; token_type: string; expires_in: number };

type AuthState = {
  user: User | null;
  /** true, dokler ob nalaganju strani preverjamo, ali obstaja seja. */
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Zahteva z dostopnim žetonom; ob poteku ga enkrat osveži in poskusi znova. */
  authRequest: <T>(path: string, options?: { method?: "GET" | "POST"; body?: unknown }) => Promise<T>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  // Dostopni žeton je samo v pomnilniku (ne v localStorage), da ga XSS ne more prebrati.
  const tokenRef = useRef<string | null>(null);

  const startSession = useCallback(async (tokens: TokenResponse) => {
    tokenRef.current = tokens.access_token;
    setUser(await apiRequest<User>("/auth/me", { token: tokens.access_token }));
  }, []);

  const refresh = useCallback(async (): Promise<boolean> => {
    try {
      await startSession(await apiRequest<TokenResponse>("/auth/refresh", { method: "POST" }));
      return true;
    } catch {
      tokenRef.current = null;
      setUser(null);
      return false;
    }
  }, [startSession]);

  useEffect(() => {
    // Obnovi sejo iz osvežilnega piškotka (npr. po ponovnem nalaganju strani).
    let active = true;
    apiRequest<TokenResponse>("/auth/refresh", { method: "POST" })
      .then((tokens) => {
        tokenRef.current = tokens.access_token;
        return apiRequest<User>("/auth/me", { token: tokens.access_token });
      })
      .then((me) => {
        if (active) setUser(me);
      })
      .catch(() => {
        tokenRef.current = null;
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await apiRequest<TokenResponse>("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      await startSession(tokens);
    },
    [startSession],
  );

  const register = useCallback(
    async (email: string, password: string) => {
      await apiRequest<User>("/auth/register", { method: "POST", body: { email, password } });
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    try {
      await apiRequest<void>("/auth/logout", { method: "POST" });
    } finally {
      tokenRef.current = null;
      setUser(null);
    }
  }, []);

  const authRequest = useCallback(
    async <T,>(path: string, options: { method?: "GET" | "POST"; body?: unknown } = {}) => {
      try {
        return await apiRequest<T>(path, { ...options, token: tokenRef.current });
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401 || !(await refresh())) throw error;
        return apiRequest<T>(path, { ...options, token: tokenRef.current });
      }
    },
    [refresh],
  );

  const value = useMemo(
    () => ({ user, loading, login, register, logout, authRequest }),
    [user, loading, login, register, logout, authRequest],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth mora biti znotraj AuthProvider.");
  return context;
}
