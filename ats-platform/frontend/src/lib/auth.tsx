import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

export interface Membership {
  org_id: string;
  org_name: string;
  role: string;
}
export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superadmin: boolean;
}
export interface MeResponse {
  user: User;
  memberships: Membership[];
  active_org_id: string | null;
  active_role: string | null;
}

interface AuthState {
  me: MeResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<MeResponse>;
  register: (payload: Record<string, unknown>) => Promise<MeResponse>;
  logout: () => void;
  refresh: () => Promise<void>;
  isRecruiter: boolean;
  isAdmin: boolean;
  isCandidate: boolean;
  isSuperadmin: boolean;
}

const Ctx = createContext<AuthState | null>(null);

import { api, orgStore, tokenStore } from "./api";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) {
      setMe(null);
      setLoading(false);
      return;
    }
    try {
      const data = await api.get<MeResponse>("/auth/me");
      setMe(data);
      if (data.active_org_id && !orgStore.get()) orgStore.set(data.active_org_id);
    } catch {
      tokenStore.clear();
      setMe(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = async (email: string, password: string) => {
    const res = await api.post<{ access_token: string }>("/auth/login", { email, password });
    tokenStore.set(res.access_token);
    const data = await api.get<MeResponse>("/auth/me");
    setMe(data);
    if (data.active_org_id) orgStore.set(data.active_org_id);
    return data;
  };

  const register = async (payload: Record<string, unknown>) => {
    const res = await api.post<{ access_token: string }>("/auth/register", payload);
    tokenStore.set(res.access_token);
    const data = await api.get<MeResponse>("/auth/me");
    setMe(data);
    if (data.active_org_id) orgStore.set(data.active_org_id);
    return data;
  };

  const logout = () => {
    tokenStore.clear();
    orgStore.clear();
    setMe(null);
  };

  const role = me?.active_role || null;
  const isSuperadmin = !!me?.user.is_superadmin;
  const isAdmin = role === "admin" || isSuperadmin;
  const isRecruiter = role === "recruiter" || isAdmin;
  const isCandidate = role === "candidate" || (!me?.memberships?.length && !!me);

  const value: AuthState = {
    me,
    loading,
    login,
    register,
    logout,
    refresh,
    isRecruiter,
    isAdmin,
    isCandidate,
    isSuperadmin,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
