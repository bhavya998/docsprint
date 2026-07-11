"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { User, AuthResponse } from "./types";
import { authApi } from "./api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("docsprint_token");
    if (token) {
      authApi
        .me()
        .then(setUser)
        .catch(() => localStorage.removeItem("docsprint_token"))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const handleAuth = async (fn: () => Promise<AuthResponse>) => {
    const response = await fn();
    localStorage.setItem("docsprint_token", response.access_token);
    setUser(response.user);
    router.push("/dashboard");
  };

  const login = (email: string, password: string) =>
    handleAuth(() => authApi.login(email, password));

  const register = (email: string, password: string) =>
    handleAuth(() => authApi.register(email, password));

  const logout = () => {
    localStorage.removeItem("docsprint_token");
    setUser(null);
    router.push("/");
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);