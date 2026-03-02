import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Box, List, ListItemButton, ListItemIcon, Tooltip, Typography } from "@mui/material";
import DashboardIcon from "@mui/icons-material/DashboardRounded";
import TurnstileIcon from "./icons/TurnstileIcon";
import PeopleIcon from "@mui/icons-material/PeopleRounded";
import DevicesIcon from "@mui/icons-material/DevicesOtherRounded";
import AssessmentIcon from "@mui/icons-material/AssessmentRounded";
import MedicalServicesIcon from "@mui/icons-material/MedicalServicesRounded";
import AdminIcon from "@mui/icons-material/AdminPanelSettingsRounded";
import EngineeringIcon from "@mui/icons-material/EngineeringRounded";
import { useAppTheme } from "@/context/ThemeContext";

export default function Sidebar() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const location = useLocation();
    const navigate = useNavigate();
    const w = tokens.sidebar.widthCollapsed;

    const navItems = [
        { path: "/dashboard", label: t("nav.dashboard"), icon: <DashboardIcon /> },
        { path: "/turnstile-journal", label: t("nav.events"), icon: <TurnstileIcon /> },
        { path: "/esmo-journal", label: t("nav.esmo"), icon: <MedicalServicesIcon /> },
        { path: "/lamp-self-rescuer", label: t("nav.tools"), icon: <EngineeringIcon /> },
        { path: "/employees", label: t("nav.employees"), icon: <PeopleIcon /> },
        { path: "/devices", label: t("nav.devices"), icon: <DevicesIcon /> },
        { path: "/reports", label: t("nav.reports"), icon: <AssessmentIcon /> },
        { path: "/user-management", label: t("adminUsers.title"), icon: <AdminIcon /> },
    ];

    return (
        <Box
            component="aside"
            sx={{
                width: w, minHeight: "100vh", position: "fixed", top: 0, left: 0, zIndex: 1200,
                display: "flex", flexDirection: "column", alignItems: "center", py: 1,
                background: tokens.bg.sidebar, backdropFilter: `blur(${tokens.glass.blur})`,
                borderRight: tokens.glass.border,
            }}
        >
            <Box sx={{ mb: 2, mt: 1.5, cursor: "pointer" }} onClick={() => navigate("/dashboard")}>
                <Box component="img" src="/logo1.png" alt="DKZ" sx={{ width: 32, height: 32, objectFit: "contain" }} />
            </Box>

            <List sx={{ width: "100%", flex: 1 }}>
                {navItems.map((item) => {
                    const active = location.pathname.startsWith(item.path);
                    return (
                        <Tooltip key={item.path} title={item.label} placement="right" arrow>
                            <ListItemButton
                                onClick={() => navigate(item.path)}
                                sx={{
                                    justifyContent: "center", py: 1.5, mx: 1, mb: 0.5,
                                    borderRadius: `${tokens.radius.sm}px`,
                                    color: active ? tokens.brand.primary : tokens.text.muted,
                                    bgcolor: active ? "rgba(59,130,246,0.12)" : "transparent",
                                    "&:hover": {
                                        bgcolor: active ? "rgba(59,130,246,0.18)" : tokens.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)",
                                        color: tokens.brand.primary,
                                    },
                                }}
                            >
                                <ListItemIcon sx={{ minWidth: 0, color: "inherit", justifyContent: "center" }}>{item.icon}</ListItemIcon>
                            </ListItemButton>
                        </Tooltip>
                    );
                })}
            </List>
        </Box>
    );
}
