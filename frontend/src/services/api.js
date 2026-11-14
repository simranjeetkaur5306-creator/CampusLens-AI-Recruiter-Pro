import axios from "axios";
import { ENDPOINTS } from "./endpoints";
import { errorMessage, fetchAllPages } from "./http";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const tokenStore = {
  get access() { return localStorage.getItem("cl_access"); },
  get refresh() { return localStorage.getItem("cl_refresh"); },
  set(access, refresh) {
    localStorage.setItem("cl_access", access);
    if (refresh) localStorage.setItem("cl_refresh", refresh);
  },
  clear() {
    localStorage.removeItem("cl_access");
    localStorage.removeItem("cl_refresh");
  },
};

const api = axios.create({ baseURL: BASE, timeout: 30000 });

api.interceptors.request.use((config) => {
  const token = tokenStore.access;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing = null;

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const url = original?.url || "";
    const isAuthCall = url.includes(ENDPOINTS.login) || url.includes(ENDPOINTS.refresh);

    if (error.response?.status === 401 && !original._retry && !isAuthCall && tokenStore.refresh) {
      original._retry = true;
      try {
        refreshing =
          refreshing ||
          axios
            .post(`${BASE}${ENDPOINTS.refresh}`, { refresh: tokenStore.refresh })
            .finally(() => { refreshing = null; });
        const { data } = await refreshing;
        tokenStore.set(data.access, data.refresh);
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch {
        tokenStore.clear();
        window.dispatchEvent(new Event("cl:logout"));
      }
    }
    return Promise.reject(error);
  }
);

export { errorMessage };

// Loads every page of a paginated list endpoint and returns the items.
export const fetchAll = (url, params) =>
  fetchAllPages((u, p) => api.get(u, { params: p }).then((r) => r.data), url, params);

export default api;