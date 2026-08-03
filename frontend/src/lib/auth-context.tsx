"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { createJwt, getSessionUser, login as awLogin, logout as awLogout, signup as awSignup } from "./appwrite";

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

function safeGet(key: string): string | null {
  try { if (typeof window==="undefined") return null; return localStorage.getItem(key) || sessionStorage.getItem(key); } catch { return null; }
}
function safeSet(key: string, val: string | null) {
  try {
    if (typeof window==="undefined") return;
    if (val) { localStorage.setItem(key, val); sessionStorage.setItem(key, val); }
    else { localStorage.removeItem(key); sessionStorage.removeItem(key); }
  } catch {}
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [jwt, setJwt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const refreshJwt = useCallback(async () => {
    try {
      const token = await createJwt();
      if (token) {
        setJwt(token);
        safeSet("arena_jwt", token);
        return token;
      }
      // keep existing jwt if create fails to avoid wiping user on transient failure
      const existing = safeGet("arena_jwt");
      if (existing) {
        setJwt(existing);
        return existing;
      }
      return null;
    } catch {
      const existing = safeGet("arena_jwt");
      if (existing) {
        setJwt(existing);
        return existing;
      }
      return null;
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const u = await getSessionUser();
        if (u) {
          setUser(u as User);
          const cached = safeGet("arena_jwt");
          if (cached) setJwt(cached);
          await refreshJwt();
          // interval refresh every 10min (JWT 15min expiry)
          intervalRef.current = setInterval(()=>{ refreshJwt(); }, 10*60*1000);
        }
      } catch {
        // don't wipe on transient error, only if truly no session
        try {
          const u2 = await getSessionUser();
          if (!u2) {
            setUser(null);
            setJwt(null);
            safeSet("arena_jwt", null);
          }
        } catch {
          setUser(null);
          setJwt(null);
          safeSet("arena_jwt", null);
        }
      } finally {
        setLoading(false);
      }
    })();
    return ()=>{ if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [refreshJwt]);

  const login = useCallback(async (email: string, password: string) => {
    const u = await awLogin(email, password);
    setUser(u as User);
    await refreshJwt();
    intervalRef.current = setInterval(()=>{ refreshJwt(); }, 10*60*1000);
  }, [refreshJwt]);

  const signup = useCallback(async (email: string, password: string, name: string) => {
    const u = await awSignup(email, password, name);
    setUser(u as User);
    await refreshJwt();
    intervalRef.current = setInterval(()=>{ refreshJwt(); }, 10*60*1000);
  }, [refreshJwt]);

  const logout = useCallback(async () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    await awLogout();
    setUser(null);
    setJwt(null);
    safeSet("arena_jwt", null);
  }, []);

  const value = useMemo(()=>({ user, jwt, loading, login, signup, logout, refreshJwt }), [user, jwt, loading, login, signup, logout, refreshJwt]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
