const CONFIGURED_BASE = String(import.meta.env.VITE_API_BASE_URL || "").trim();
const BASE = CONFIGURED_BASE || "/api/v1";
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";
const TOKEN_KEY = "minetrack_token";

function getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const token = getToken();
    const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (init.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";

    const res = await fetch(`${BASE}${path}`, { ...init, headers });

    if (res.status === 401) {
        localStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(TOKEN_KEY);
        window.location.href = "/login";
        throw new Error("Unauthorized");
    }
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
    }
    if (res.status === 204) return null as T;
    return res.json();
}

export const apiClient = {
    baseUrl: BASE,
    useMocks: USE_MOCKS,
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body: unknown) =>
        request<T>(path, { method: "POST", body: JSON.stringify(body) }),
    put: <T>(path: string, body: unknown) =>
        request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
    del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
