import { Box } from "@mui/material";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import { useAppTheme } from "@/context/ThemeContext";

export default function Layout() {
    const { tokens } = useAppTheme();
    return (
        <Box sx={{ display: "flex", minHeight: "100vh" }}>
            <Sidebar />
            <Box sx={{ flex: 1, ml: `${tokens.sidebar.widthCollapsed}px`, display: "flex", flexDirection: "column" }}>
                <TopBar />
                <Box component="main" sx={{ flex: 1, p: 3, overflow: "auto" }}>
                    <Outlet />
                </Box>
            </Box>
        </Box>
    );
}
