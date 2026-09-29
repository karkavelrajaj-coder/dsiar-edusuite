import { createContext, useContext, useEffect, useState } from "react";
import { getPlatformToken, platformApi, setPlatformToken } from "../api/client";

const PlatformAuthContext = createContext(null);

export function PlatformAuthProvider({ children }) {
  const [admin, setAdmin] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getPlatformToken()) {
      setLoading(false);
      return;
    }
    platformApi
      .get("/platform/auth/me")
      .then((res) => setAdmin(res.data))
      .catch(() => {
        setPlatformToken(null);
        setAdmin(null);
      })
      .finally(() => setLoading(false));
  }, []);

  async function login(email, password) {
    const res = await platformApi.post("/platform/auth/login", { email, password });
    setPlatformToken(res.data.access_token);
    const { access_token, ...adminFields } = res.data;
    setAdmin(adminFields);
    return adminFields;
  }

  async function logout() {
    try {
      await platformApi.post("/platform/auth/logout");
    } finally {
      setPlatformToken(null);
      setAdmin(null);
    }
  }

  return (
    <PlatformAuthContext.Provider value={{ admin, loading, login, logout }}>
      {children}
    </PlatformAuthContext.Provider>
  );
}

export function usePlatformAuth() {
  const ctx = useContext(PlatformAuthContext);
  if (!ctx) throw new Error("usePlatformAuth must be used within PlatformAuthProvider");
  return ctx;
}
