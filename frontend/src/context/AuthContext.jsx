import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // No stored token -> definitely logged out, skip the network round trip.
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api
      .get("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => {
        setToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  async function login(companyCode, email, password) {
    const res = await api.post("/auth/login", { company_code: companyCode, email, password });
    setToken(res.data.access_token);
    const { access_token, ...userFields } = res.data;
    setUser(userFields);
    try {
      // Remembered only so the login form can pre-fill it next time — never
      // used to decide access; the backend always re-checks the code.
      localStorage.setItem("lms_last_company_code", companyCode);
    } catch {
      // Storage can be unavailable (private browsing); not essential.
    }
    return userFields;
  }

  async function logout() {
    try {
      await api.post("/auth/logout");
    } finally {
      setToken(null);
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
