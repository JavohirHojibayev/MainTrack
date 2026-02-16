import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { apiClient } from "@/api/client";

interface AuthState {
    token: string | null;
    user: string | null;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthState>({
    token: null,
    user: null,
    login: async () => { },
    logout: () => { },
});

export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setToken] = useState<string | null>(localStorage.getItem("minetrack_token"));
    const [user, setUser] = useState<string | null>(localStorage.getItem("minetrack_user"));

    const login = useCallback(async (username: string, password: string) => {
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
        localStorage.setItem("minetrack_token", data.access_token);
        localStorage.setItem("minetrack_user", username);
        setToken(data.access_token);
        setUser(username);
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem("minetrack_token");
        localStorage.removeItem("minetrack_user");
        setToken(null);
        setUser(null);
    }, []);

    return (
        <AuthContext.Provider value={{ token, user, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
