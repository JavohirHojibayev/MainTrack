import { Paper, type PaperProps } from "@mui/material";
import { useAppTheme } from "@/context/ThemeContext";

interface GlassCardProps extends PaperProps {
    glow?: boolean;
}

export default function GlassCard({ glow, sx, children, ...rest }: GlassCardProps) {
    const { tokens } = useAppTheme();
    const isDark = tokens.mode === "dark";
    return (
        <Paper
            elevation={0}
            sx={{
                p: 3,
                borderRadius: `${tokens.radius.md}px`,
                background: isDark
                    ? "linear-gradient(135deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.05) 100%)"
                    : "linear-gradient(135deg, rgba(255,255,255,0.70) 0%, rgba(255,255,255,0.50) 100%)",
                backdropFilter: `blur(${tokens.glass.blur})`,
                WebkitBackdropFilter: `blur(${tokens.glass.blur})`,
                border: tokens.glass.border,
                boxShadow: glow
                    ? `0 0 30px ${tokens.brand.primary}33, ${tokens.glass.shadow}`
                    : tokens.glass.shadow,
                transition: "all 0.3s ease",
                "&:hover": {
                    border: tokens.glass.borderHover,
                    background: isDark
                        ? "linear-gradient(135deg, rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.07) 100%)"
                        : "linear-gradient(135deg, rgba(255,255,255,0.80) 0%, rgba(255,255,255,0.60) 100%)",
                },
                ...sx,
            }}
            {...rest}
        >
            {children}
        </Paper>
    );
}
