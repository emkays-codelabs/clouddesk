"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, clearToken, getToken, setToken } from "./api";
import type { Role, User } from "./types";

const RANK: Record<Role, number> = { viewer: 1, agent: 2, admin: 3 };

/** Viewers read; agents and admins act (run, reply, approve, escalate). */
export function canAct(user: User | null | undefined): boolean {
  return !!user && RANK[user.role] >= RANK.agent;
}

export function isAdmin(user: User | null | undefined): boolean {
  return !!user && user.role === "admin";
}

type AuthState = {
  user: User | null;
  ready: boolean;
  login: (email: string) => Promise<User>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function restore() {
      if (!getToken()) {
        setReady(true);
        return;
      }
      try {
        const me = await api.me();
        if (!cancelled) setUser(me);
      } catch {
        /* a 401 already cleared the token and sent the browser to /login */
      } finally {
        if (!cancelled) setReady(true);
      }
    }
    void restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string) => {
    const result = await api.login(email);
    setToken(result.access_token);
    setUser(result.user);
    return result.user;
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    if (typeof window !== "undefined") window.location.assign("/login");
  }, []);

  return <AuthContext.Provider value={{ user, ready, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
