import { createContext, useCallback, useContext, useEffect, useState } from "react";
import api, { tokenStore } from "../services/api";
import { ENDPOINTS } from "../services/endpoints";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    if (!tokenStore.access) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get(ENDPOINTS.me);
      setUser(data);
    } catch {
      tokenStore.clear();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
    const onLogout = () => setUser(null);
    window.addEventListener("cl:logout", onLogout);
    return () => window.removeEventListener("cl:logout", onLogout);
  }, [loadUser]);

  const login = async (email, password) => {
    const { data } = await api.post(ENDPOINTS.login, { email, password });
    tokenStore.set(data.access, data.refresh);
    const me = await api.get(ENDPOINTS.me);
    setUser(me.data);
    return me.data;
  };

  const logout = () => {
    tokenStore.clear();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthContext);
