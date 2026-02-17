import { createContext, useContext, useState } from "react";
import { Box } from "@mui/material";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import { useAppTheme } from "@/context/ThemeContext";

interface LayoutContextType {
    searchQuery: string;
    setSearchQuery: (query: string) => void;
}

const LayoutContext = createContext<LayoutContextType | undefined>(undefined);

export const useLayout = () => {
    const context = useContext(LayoutContext);
    if (!context) {
        throw new Error("useLayout must be used within a Layout");
    }
    return context;
};

export default function Layout() {
    const { tokens } = useAppTheme();
    const [searchQuery, setSearchQuery] = useState("");

    return (
        <LayoutContext.Provider value={{ searchQuery, setSearchQuery }}>
            <Box sx={{ display: "flex", minHeight: "100vh" }}>
                <Sidebar />
                <Box sx={{ flex: 1, ml: `${tokens.sidebar.widthCollapsed}px`, display: "flex", flexDirection: "column" }}>
                    <TopBar />
                    <Box component="main" sx={{ flex: 1, p: 3, overflow: "auto" }}>
                        <Outlet context={{ searchQuery }} />
                    </Box>
                </Box>
            </Box>
        </LayoutContext.Provider>
    );
}
