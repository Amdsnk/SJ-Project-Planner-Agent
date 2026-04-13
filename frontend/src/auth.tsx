import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { api } from "./api";

export type AuthUser = {
  id: number;
  org_id: number;
  email: string;
  full_name: string;
  role: "admin" | "reviewer" | "viewer" | string;
};

type AuthCtx = {
  user: AuthUser | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
};

const Ctx = createContext<AuthCtx>({} as AuthCtx);
const TOKEN_KEY = "sj_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  // React to 401s by clearing local auth state. The request-side Authorization
  // header is attached by a module-level interceptor in api.ts to avoid a race
  // with this effect on token changes.
  useEffect(() => {
    const resId = api.interceptors.response.use(
      r => r,
      err => {
        if (err?.response?.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          setToken(null);
          setUser(null);
        }
        return Promise.reject(err);
      },
    );
    return () => { api.interceptors.response.eject(resId); };
  }, []);

  // Resolve current user when we have a token.
  useEffect(() => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    api.get<AuthUser>("/auth/me")
      .then(r => setUser(r.data))
      .catch(() => { /* interceptor handles 401 */ })
      .finally(() => setLoading(false));
  }, [token]);

  const login = async (email: string, password: string) => {
    const r = await api.post("/auth/login", { email, password });
    const t = r.data.access_token as string;
    localStorage.setItem(TOKEN_KEY, t);
    setToken(t);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  };

  return <Ctx.Provider value={{ user, token, login, logout, loading }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
