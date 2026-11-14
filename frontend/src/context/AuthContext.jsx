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
    // The login response already contains the user; fall back to /me if it does not.
    const me = data.user ?? (await api.get(ENDPOINTS.me)).data;
    setUser(me);
    return me;
  };

  const logout = async () => {
    const refresh = tokenStore.refresh;
    tokenStore.clear();
    setUser(null);
    if (refresh) {
      // Best effort: ask the server to blacklist the refresh token. Failure changes nothing for the user.
      try {
        await api.post(ENDPOINTS.logout, { refresh });
      } catch {
        /* ignore */
      }
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthContext);