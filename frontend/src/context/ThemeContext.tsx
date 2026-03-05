import { createContext, useContext, useState, useMemo, useCallback, type ReactNode } from "react";
import { ThemeProvider as MuiThemeProvider, CssBaseline } from "@mui/material";
import { buildTheme } from "@/theme";
import { darkTokens, lightTokens, type ThemeTokens } from "@/theme/tokens";

type Mode = "light" | "dark";
const THEME_KEY = "minetrack_theme";
const THEME_INIT_KEY = "minetrack_theme_initialized";

function resolveInitialMode(): Mode {
    if (typeof window === "undefined") return "light";

    const initialized = localStorage.getItem(THEME_INIT_KEY) === "1";
    const stored = localStorage.getItem(THEME_KEY);

    // Migration-safe first run: force default day/light once.
    if (!initialized) {
        localStorage.setItem(THEME_KEY, "light");
        localStorage.setItem(THEME_INIT_KEY, "1");
        return "light";
    }

    if (stored === "light" || stored === "dark") return stored;
    localStorage.setItem(THEME_KEY, "light");
    return "light";
}

interface ThemeCtx {
    mode: Mode;
    tokens: ThemeTokens;
    toggleMode: () => void;
}

const ThemeContext = createContext<ThemeCtx>({
    mode: "light",
    tokens: lightTokens,
    toggleMode: () => { },
});

export function AppThemeProvider({ children }: { children: ReactNode }) {
    const [mode, setMode] = useState<Mode>(
        () => resolveInitialMode()
    );

    const toggleMode = useCallback(() => {
        setMode((prev) => {
            const next = prev === "dark" ? "light" : "dark";
            localStorage.setItem(THEME_KEY, next);
            localStorage.setItem(THEME_INIT_KEY, "1");
            return next;
        });
    }, []);

    const tokens = mode === "dark" ? darkTokens : lightTokens;
    const theme = useMemo(() => buildTheme(tokens), [tokens]);

    return (
        <ThemeContext.Provider value={{ mode, tokens, toggleMode }}>
            <MuiThemeProvider theme={theme}>
                <CssBaseline />
                {children}
            </MuiThemeProvider>
        </ThemeContext.Provider>
    );
}

export const useAppTheme = () => useContext(ThemeContext);
