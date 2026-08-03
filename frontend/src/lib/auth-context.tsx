"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  createJwt,
  getSessionUser,
  login as awLogin,
  logout as awLogout,
  signup as awSignup,
} from "./appwrite";

type User = { $id: string; name?: string; email?: string };

type AuthState = {
  user: User | null;
  jwt: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshJwt: () => Promise<string | null>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [jwt, setJwt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshJwt = useCallback(async () => {
    const token = await createJwt();
    setJwt(token);
    if (token) sessionStorage.setItem("arena_jwt", token);
    else sessionStorage.removeItem("arena_jwt");
    return token;
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const u = await getSessionUser();
        if (u) {
          setUser(u as User);
          const token = await refreshJwt();
          if (!token) setUser(null);
        }
      } catch {
        setUser(null);
        setJwt(null);
        sessionStorage.removeItem("arena_jwt");
      } finally {
        setLoading(false);
      }
    })();
  }, [refreshJwt]);

  const login = useCallback(
    async (email: string, password: string) => {
      const u = await awLogin(email, password);
      setUser(u as User);
      await refreshJwt();
    },
    [refreshJwt],
  );

  const signup = useCallback(
    async (email: string, password: string, name: string) => {
      const u = await awSignup(email, password, name);
      setUser(u as User);
      await refreshJwt();
    },
    [refreshJwt],
  );

  const logout = useCallback(async () => {
    await awLogout();
    setUser(null);
    setJwt(null);
    sessionStorage.removeItem("arena_jwt");
  }, []);

  const value = useMemo(
    () => ({ user, jwt, loading, login, signup, logout, refreshJwt }),
    [user, jwt, loading, login, signup, logout, refreshJwt],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
