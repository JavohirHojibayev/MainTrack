import { createContext, useContext, useState, useMemo, useCallback, type ReactNode } from "react";
import { ThemeProvider as MuiThemeProvider, CssBaseline } from "@mui/material";
import { buildTheme } from "@/theme";
import { darkTokens, lightTokens, type ThemeTokens } from "@/theme/tokens";

type Mode = "light" | "dark";

interface ThemeCtx {
    mode: Mode;
    tokens: ThemeTokens;
    toggleMode: () => void;
}

const ThemeContext = createContext<ThemeCtx>({
    mode: "dark",
    tokens: darkTokens,
    toggleMode: () => { },
});

export function AppThemeProvider({ children }: { children: ReactNode }) {
    const [mode, setMode] = useState<Mode>(
        () => (localStorage.getItem("minetrack_theme") as Mode) || "dark"
    );

    const toggleMode = useCallback(() => {
        setMode((prev) => {
            const next = prev === "dark" ? "light" : "dark";
            localStorage.setItem("minetrack_theme", next);
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
