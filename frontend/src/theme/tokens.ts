/* ── MineTrack Design Tokens — Light + Dark ── */

const shared = {
    radius: { sm: 8, md: 16, lg: 24 },
    sidebar: { widthCollapsed: 72, widthExpanded: 240 },
    topbar: { height: 64 },
    brand: {
        primary: "#3b82f6",
        primaryHover: "#2563eb",
        secondary: "#06b6d4",
        accent: "#8b5cf6",
    },
    status: {
        ok: "#22c55e",
        okBg: "rgba(34,197,94,0.15)",
        warning: "#f59e0b",
        warningBg: "rgba(245,158,11,0.15)",
        blocked: "#ef4444",
        blockedBg: "rgba(239,68,68,0.15)",
        error: "#ef4444", // Alias for blocked
        offline: "#6b7280",
        offlineBg: "rgba(107,114,128,0.15)",
        info: "#3b82f6",
        infoBg: "rgba(59,130,246,0.15)",
    },
};

export const darkTokens = {
    ...shared,
    mode: "dark" as const,
    bg: {
        gradient: "linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #020617 100%)",
        surface: "rgba(255,255,255,0.06)",
        card: "rgba(255,255,255,0.08)",
        cardHover: "rgba(255,255,255,0.12)",
        sidebar: "rgba(10,15,28,0.92)",
        topbar: "rgba(15,23,36,0.85)",
        tableRow: "rgba(255,255,255,0.03)",
        tableRowAlt: "rgba(255,255,255,0.05)",
        tableHeader: "rgba(15,23,42,0.95)",
        input: "rgba(255,255,255,0.07)",
        paper: "#111827",
    },
    text: {
        primary: "#e2e8f0",
        main: "#e2e8f0", // Alias for primary
        secondary: "#94a3b8",
        muted: "#64748b",
        heading: "#f1f5f9",
    },
    glass: {
        blur: "40px",
        border: "1px solid rgba(255,255,255,0.1)",
        borderHover: "1px solid rgba(255,255,255,0.2)",
        shadow: "0 25px 50px -12px rgba(0,0,0,0.5), inset 0 0 0 1px rgba(255,255,255,0.1)",
        shadowSm: "0 4px 6px -1px rgba(0,0,0,0.3), inset 0 0 0 1px rgba(255,255,255,0.1)",
    },
};

export const lightTokens = {
    ...shared,
    mode: "light" as const,
    bg: {
        gradient: "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #cbd5e1 100%)",
        surface: "rgba(255,255,255,0.65)",
        card: "rgba(255,255,255,0.55)",
        cardHover: "rgba(255,255,255,0.72)",
        sidebar: "rgba(255,255,255,0.88)",
        topbar: "rgba(255,255,255,0.80)",
        tableRow: "rgba(0,0,0,0.02)",
        tableRowAlt: "rgba(0,0,0,0.04)",
        tableHeader: "rgba(240,244,250,0.95)",
        input: "rgba(0,0,0,0.04)",
        paper: "#ffffff",
    },
    text: {
        primary: "#1e293b",
        main: "#1e293b", // Alias for primary
        secondary: "#475569",
        muted: "#94a3b8",
        heading: "#0f172a",
    },
    glass: {
        blur: "40px",
        border: "1px solid rgba(255,255,255,0.4)",
        borderHover: "1px solid rgba(255,255,255,0.6)",
        shadow: "0 25px 50px -12px rgba(0,0,0,0.1), inset 0 0 0 1px rgba(255,255,255,0.4)",
        shadowSm: "0 4px 6px -1px rgba(0,0,0,0.05), inset 0 0 0 1px rgba(255,255,255,0.3)",
    },
};

export type ThemeTokens = typeof darkTokens | typeof lightTokens;
