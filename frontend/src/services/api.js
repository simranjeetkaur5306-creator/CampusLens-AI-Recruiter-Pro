import axios from "axios";
import { ENDPOINTS } from "./endpoints";

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

export function errorMessage(err) {
  if (!err.response) return "Cannot reach the server. Is the backend running?";
  const data = err.response.data;
  if (typeof data === "string") return "Something went wrong. Please try again.";
  if (data?.detail) return data.detail;
  const first = data && Object.values(data)[0];
  if (Array.isArray(first)) return first[0];
  if (typeof first === "string") return first;
  return "Something went wrong. Please try again.";
}

export default api;
