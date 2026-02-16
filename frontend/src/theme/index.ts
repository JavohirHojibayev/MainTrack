import { createTheme, alpha } from "@mui/material/styles";
import { type ThemeTokens } from "./tokens";

export function buildTheme(t: ThemeTokens) {
    const isDark = t.mode === "dark";
    return createTheme({
        palette: {
            mode: t.mode,
            primary: { main: t.brand.primary },
            secondary: { main: t.brand.secondary },
            background: { default: isDark ? "#0f1724" : "#e8edf5", paper: t.bg.paper },
            text: { primary: t.text.primary, secondary: t.text.secondary },
            success: { main: t.status.ok },
            warning: { main: t.status.warning },
            error: { main: t.status.blocked },
            info: { main: t.status.info },
        },
        typography: {
            fontFamily: "'Inter', sans-serif",
            h4: {
                fontWeight: 700, fontSize: "1.75rem",
                background: `linear-gradient(135deg, ${t.brand.primary}, ${t.brand.secondary})`,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
            },
            h5: {
                fontWeight: 600, fontSize: "1.35rem",
                background: `linear-gradient(135deg, ${t.brand.primary}, ${t.brand.secondary})`,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
            },
            h6: { fontWeight: 600, fontSize: "1.1rem", color: t.text.heading },
            body1: { fontSize: "0.938rem", color: t.text.primary },
            body2: { fontSize: "0.813rem", color: t.text.secondary },
            button: { textTransform: "none" as const, fontWeight: 600 },
        },
        shape: { borderRadius: t.radius.md },
        components: {
            MuiCssBaseline: {
                styleOverrides: {
                    body: {
                        background: t.bg.gradient,
                        minHeight: "100vh",
                        backgroundSize: "600% 600%",
                        animation: "gradient-animation 8s ease infinite",
                    },
                    "input:-webkit-autofill, input:-webkit-autofill:hover, input:-webkit-autofill:focus, input:-webkit-autofill:active": {
                        WebkitBoxShadow: "0 0 0 1000px transparent inset !important",
                        WebkitTextFillColor: `${t.text.primary} !important`,
                        transition: "background-color 5000s ease-in-out 0s",
                    },
                    "*::-webkit-scrollbar": { width: 6, height: 6 },
                    "*::-webkit-scrollbar-thumb": {
                        background: isDark ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.15)",
                        borderRadius: 3,
                    },
                },
            },
            MuiPaper: {
                styleOverrides: {
                    root: {
                        backgroundImage: "none",
                        backgroundColor: t.bg.card,
                        backdropFilter: `blur(${t.glass.blur})`,
                        border: t.glass.border,
                        boxShadow: t.glass.shadow,
                    },
                },
            },
            MuiButton: {
                styleOverrides: {
                    contained: {
                        background: `linear-gradient(135deg, ${t.brand.primary}, ${t.brand.secondary})`,
                        color: "#fff",
                        boxShadow: `0 4px 14px ${alpha(t.brand.primary, 0.4)}`,
                        "&:hover": {
                            background: `linear-gradient(135deg, ${t.brand.primaryHover}, ${t.brand.secondary})`,
                        },
                    },
                    outlined: {
                        borderColor: isDark ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.15)",
                        "&:hover": {
                            borderColor: isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)",
                            background: isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.04)",
                        },
                    },
                },
            },
            MuiTextField: {
                defaultProps: { variant: "outlined", size: "small" },
                styleOverrides: {
                    root: {
                        "& .MuiOutlinedInput-root": {
                            backgroundColor: "rgba(255, 255, 255, 0.05)",
                            borderRadius: t.radius.sm,
                            transition: "all 0.2s ease-in-out",
                            "& fieldset": { borderColor: isDark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.12)" },
                            "&:hover fieldset": { borderColor: isDark ? "rgba(255,255,255,0.25)" : "rgba(0,0,0,0.25)" },
                            "&.Mui-focused fieldset": { borderColor: t.brand.primary },
                            "& input": {
                                backgroundColor: "transparent !important",
                            }
                        },
                    },
                },
            },
            MuiTableHead: {
                styleOverrides: {
                    root: {
                        "& .MuiTableCell-head": {
                            fontWeight: 600,
                            color: t.text.heading,
                            backgroundColor: t.bg.tableHeader,
                        },
                    },
                },
            },
            MuiTableCell: {
                styleOverrides: {
                    root: { borderColor: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" },
                },
            },
            MuiDrawer: {
                styleOverrides: {
                    paper: {
                        backgroundColor: isDark ? t.bg.sidebar : t.bg.paper,
                        backdropFilter: `blur(${t.glass.blur})`,
                        border: "none",
                    },
                },
            },
            MuiChip: {
                styleOverrides: { root: { fontWeight: 600, fontSize: "0.75rem" } },
            },
        },
    });
}
