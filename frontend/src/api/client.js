import axios from "axios";

// In dev, Vite proxies /api -> http://localhost:8000 (see vite.config.js).
// In production, set VITE_API_BASE_URL to the deployed Render backend URL.
const baseURL = import.meta.env.VITE_API_BASE_URL || "/api";

const TOKEN_KEY = "dsiar_access_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

// Builds an absolute URL to a backend-served static asset (course
// thumbnails, etc). baseURL already includes "/api" (e.g.
// "https://dsiar-lms-backend.onrender.com/api" in prod, or just "/api" in
// dev behind the Vite proxy) — a plain "/api/static/..." path would
// resolve against the FRONTEND's own origin in production since frontend
// and backend are different domains, so this always builds it off the
// same base the API client itself uses.
export function staticUrl(relativePath) {
  const cleaned = relativePath.replace(/^assets\//, "");
  return `${baseURL}/static/${cleaned.split("/").map(encodeURIComponent).join("/")}`;
}

export const api = axios.create({
  baseURL,
  withCredentials: true, // also sends the cookie, useful in local dev (same-origin via the Vite proxy)
});

// The deployed frontend and backend live on different onrender.com
// subdomains, and browsers (Incognito especially) block third-party
// cookies between them — so the cookie alone isn't reliable in
// production. Sending the JWT explicitly as a Bearer header works
// regardless of cookie policy, and is what the backend checks first.
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail || err.message || "Something went wrong.";
    return Promise.reject(new Error(message));
  }
);

// --- Platform (Super Admin) session — completely separate from the tenant
// session above: its own token, its own storage key, never sent on a
// regular /api/* tenant request and vice versa. A Super Admin isn't a
// member of any client company, so mixing the two tokens up would be a
// real isolation bug, not just a UX one.
const PLATFORM_TOKEN_KEY = "dsiar_platform_access_token";

export function getPlatformToken() {
  return localStorage.getItem(PLATFORM_TOKEN_KEY);
}

export function setPlatformToken(token) {
  if (token) localStorage.setItem(PLATFORM_TOKEN_KEY, token);
  else localStorage.removeItem(PLATFORM_TOKEN_KEY);
}

export const platformApi = axios.create({ baseURL, withCredentials: true });

platformApi.interceptors.request.use((config) => {
  const token = getPlatformToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

platformApi.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err.response?.data?.detail || err.message || "Something went wrong.";
    return Promise.reject(new Error(message));
  }
);
