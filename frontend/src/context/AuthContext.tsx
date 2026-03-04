import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { apiClient } from "@/api/client";

const TOKEN_KEY = "minetrack_token";
const USER_KEY = "minetrack_user";
const ROLE_KEY = "minetrack_role";

function getStoredValue(key: string): string | null {
    return localStorage.getItem(key) ?? sessionStorage.getItem(key);
}

function decodeRoleFromJwt(token: string | null): string | null {
    if (!token) return null;
    try {
        const parts = token.split(".");
        if (parts.length < 2) return null;
        const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
        const padded = payload + "=".repeat((4 - (payload.length % 4)) % 4);
        const parsed = JSON.parse(atob(padded));
        const role = typeof parsed?.role === "string" ? parsed.role.trim() : "";
        return role || null;
    } catch {
        return null;
    }
}

interface AuthState {
    token: string | null;
    user: string | null;
    role: string | null;
    login: (username: string, password: string, rememberMe?: boolean) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthState>({
    token: null,
    user: null,
    role: null,
    login: async () => { },
    logout: () => { },
});

export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setToken] = useState<string | null>(() => getStoredValue(TOKEN_KEY));
    const [user, setUser] = useState<string | null>(() => getStoredValue(USER_KEY));
    const [role, setRole] = useState<string | null>(() => {
        const storedRole = getStoredValue(ROLE_KEY);
        if (storedRole) return storedRole;
        return decodeRoleFromJwt(getStoredValue(TOKEN_KEY));
    });

    const login = useCallback(async (username: string, password: string, rememberMe = true) => {
        const body = new URLSearchParams();
        body.set("username", username);
        body.set("password", password);

        const res = await fetch(`${apiClient.baseUrl}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body,
        });
        if (!res.ok) throw new Error("Invalid username or password");
        const data = await res.json();
        const nextRole = decodeRoleFromJwt(data.access_token);

        const activeStorage = rememberMe ? localStorage : sessionStorage;
        const inactiveStorage = rememberMe ? sessionStorage : localStorage;

        inactiveStorage.removeItem(TOKEN_KEY);
        inactiveStorage.removeItem(USER_KEY);
        inactiveStorage.removeItem(ROLE_KEY);

        activeStorage.setItem(TOKEN_KEY, data.access_token);
        activeStorage.setItem(USER_KEY, username);
        if (nextRole) {
            activeStorage.setItem(ROLE_KEY, nextRole);
        } else {
            activeStorage.removeItem(ROLE_KEY);
        }
        setToken(data.access_token);
        setUser(username);
        setRole(nextRole);
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        localStorage.removeItem(ROLE_KEY);
        sessionStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(USER_KEY);
        sessionStorage.removeItem(ROLE_KEY);
        setToken(null);
        setUser(null);
        setRole(null);
    }, []);

    return (
        <AuthContext.Provider value={{ token, user, role, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
