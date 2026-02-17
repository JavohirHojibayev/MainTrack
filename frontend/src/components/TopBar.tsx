import { useTranslation } from "react-i18next";
import { Box, Typography, IconButton, TextField, InputAdornment, Select, MenuItem } from "@mui/material";
import SearchIcon from "@mui/icons-material/SearchRounded";
import LogoutIcon from "@mui/icons-material/LogoutRounded";
import LightModeIcon from "@mui/icons-material/LightModeRounded";
import DarkModeIcon from "@mui/icons-material/DarkModeRounded";
import LanguageIcon from "@mui/icons-material/LanguageRounded";
import { useAppTheme } from "@/context/ThemeContext";
import { useAuth } from "@/context/AuthContext";
import { useLayout } from "./Layout";

const LANGUAGES = [
    { code: "en", label: "EN" },
    { code: "ru", label: "RU" },
    { code: "uz", label: "UZ" },
];

export default function TopBar() {
    const { t, i18n } = useTranslation();
    const { tokens, mode, toggleMode } = useAppTheme();
    const { user, logout } = useAuth();
    const { searchQuery, setSearchQuery } = useLayout();

    const changeLang = (lng: string) => {
        i18n.changeLanguage(lng);
        localStorage.setItem("minetrack_lang", lng);
    };

    return (
        <Box
            component="header"
            sx={{
                height: tokens.topbar.height, display: "flex", alignItems: "center", px: 3, gap: 2,
                background: tokens.bg.topbar, backdropFilter: `blur(${tokens.glass.blur})`,
                borderBottom: tokens.glass.border,
            }}
        >
            <Typography variant="h6" sx={{
                fontWeight: 800, fontSize: "1.5rem", mr: 2,
                color: "#3b82f6",
            }}>
                {t("app.name")}
            </Typography>

            <TextField
                placeholder={t("topbar.search")}
                size="small"
                sx={{ width: 300 }}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                InputProps={{
                    startAdornment: (
                        <InputAdornment position="start">
                            <SearchIcon sx={{ color: tokens.text.muted, fontSize: 20 }} />
                        </InputAdornment>
                    ),
                }}
            />

            {/* Marquee Text */}
            <Box sx={{ flex: 1, overflow: "hidden", position: "relative", height: "100%", mx: -2 }}>
                <Typography
                    variant="h6"
                    sx={{
                        whiteSpace: "nowrap",
                        color: tokens.status.warning,
                        fontWeight: 700,
                        fontSize: "1.15rem",
                        position: "absolute",
                        top: "50%",
                        transform: "translateY(-50%)",
                        animation: "marquee 15s linear infinite",
                        width: "100%",
                        textAlign: "center" // Center text when not scrolling if animation stops (fallback)
                    }}
                >
                    {t("app.testMode")}
                </Typography>
            </Box>

            {/* Language Switcher */}
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                <LanguageIcon sx={{ color: tokens.text.muted, fontSize: 18 }} />
                <Select
                    value={i18n.language}
                    onChange={(e) => changeLang(e.target.value)}
                    size="small"
                    variant="standard"
                    disableUnderline
                    sx={{
                        color: tokens.text.secondary,
                        fontSize: "0.813rem",
                        fontWeight: 600,
                        "& .MuiSelect-select": { py: 0 },
                    }}
                >
                    {LANGUAGES.map((l) => (
                        <MenuItem key={l.code} value={l.code}>{l.label}</MenuItem>
                    ))}
                </Select>
            </Box>

            {/* Theme Toggle */}
            <IconButton onClick={toggleMode} size="small" sx={{ color: tokens.text.muted }} title={t("topbar.theme")}>
                {mode === "dark" ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
            </IconButton>

            <Typography variant="body2" sx={{ color: tokens.text.secondary }}>{user ?? "admin"}</Typography>

            <IconButton onClick={logout} size="small" sx={{ color: tokens.text.muted }}>
                <LogoutIcon fontSize="small" />
            </IconButton>
        </Box>
    );
}
