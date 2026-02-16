import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Box, Typography, TextField, Button, Alert, InputAdornment, IconButton } from "@mui/material";
import VisibilityIcon from "@mui/icons-material/VisibilityRounded";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOffRounded";
import { ThemeProvider } from "@mui/material";
import { useAuth } from "@/context/AuthContext";
import { useAppTheme } from "@/context/ThemeContext";
import { buildTheme } from "@/theme";
import { darkTokens } from "@/theme/tokens";

const loginTheme = buildTheme(darkTokens);

export default function LoginPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const { login } = useAuth();
    const navigate = useNavigate();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            await login(username, password);
            navigate("/dashboard", { replace: true });
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : t("auth.loginFailed"));
        } finally {
            setLoading(false);
        }
    };

    return (
        <ThemeProvider theme={loginTheme}>
            <Box sx={{
                minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
                position: "relative", overflow: "hidden",
            }}>
                {/* Background image */}
                <Box sx={{
                    position: "absolute", inset: 0, zIndex: 0,
                    backgroundImage: 'url("/01.png")',
                    backgroundSize: "cover", backgroundPosition: "center",
                    filter: "brightness(0.4)",
                }} />
                {/* Dark overlay */}
                <Box sx={{
                    position: "absolute", inset: 0, zIndex: 1,
                    background: "linear-gradient(135deg, rgba(15,23,36,0.7) 0%, rgba(13,27,42,0.5) 100%)",
                }} />
                <Box
                    component="form"
                    onSubmit={handleSubmit}
                    sx={{
                        width: 420, p: 5, borderRadius: `${tokens.radius.lg}px`, zIndex: 2,
                        background: "rgba(255, 255, 255, 0.05)",
                        backdropFilter: `blur(${darkTokens.glass.blur})`,
                        WebkitBackdropFilter: `blur(${darkTokens.glass.blur})`,
                        border: darkTokens.glass.border,
                        boxShadow: darkTokens.glass.shadow,
                    }}
                >
                    <Typography variant="h4" sx={{ mb: 0.5, textAlign: "center" }}>{t("app.name")}</Typography>
                    <Typography variant="body2" sx={{ mb: 4, textAlign: "center", color: tokens.text.muted }}>{t("app.subtitle")}</Typography>
                    {error && <Alert severity="error" sx={{ mb: 2, bgcolor: tokens.status.blockedBg, color: tokens.status.blocked }}>{error}</Alert>}
                    <TextField label={t("auth.username")} fullWidth value={username} onChange={(e) => setUsername(e.target.value)} sx={{ mb: 2 }} autoFocus />
                    <TextField
                        label={t("auth.password")}
                        type={showPassword ? "text" : "password"}
                        fullWidth
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        sx={{ mb: 3 }}
                        InputProps={{
                            endAdornment: (
                                <InputAdornment position="end">
                                    <IconButton onClick={() => setShowPassword((v) => !v)} edge="end" size="small" sx={{ color: tokens.text.muted }}>
                                        {showPassword ? <VisibilityOffIcon fontSize="small" /> : <VisibilityIcon fontSize="small" />}
                                    </IconButton>
                                </InputAdornment>
                            ),
                        }}
                    />
                    <Button type="submit" variant="contained" fullWidth size="large" disabled={loading}>
                        {loading ? t("auth.signingIn") : t("auth.signIn")}
                    </Button>
                </Box>
            </Box>
        </ThemeProvider>
    );
}
