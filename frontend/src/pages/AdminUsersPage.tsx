import { useTranslation } from "react-i18next";
import { Box, Typography, Table, TableBody, TableCell, TableHead, TableRow, Select, MenuItem } from "@mui/material";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";

const mockUsers = [
    { id: 1, username: "admin", role: "admin", is_active: true },
    { id: 2, username: "dispatcher", role: "dispatcher", is_active: true },
    { id: 3, username: "medical", role: "medical", is_active: true },
    { id: 4, username: "warehouse", role: "warehouse", is_active: true },
    { id: 5, username: "viewer", role: "viewer", is_active: true },
];
const roles = ["admin", "superadmin", "dispatcher", "medical", "warehouse", "viewer"];

export default function AdminUsersPage() {
    const { t } = useTranslation();
    return (
        <Box>
            <Typography variant="h4" sx={{
                mb: 3,
                background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                display: "inline-block"
            }}>{t("adminUsers.title")}</Typography>
            <GlassCard>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>{t("adminUsers.col.id")}</TableCell><TableCell>{t("adminUsers.col.username")}</TableCell>
                            <TableCell>{t("adminUsers.col.role")}</TableCell><TableCell>{t("adminUsers.col.status")}</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {mockUsers.map((u) => (
                            <TableRow key={u.id}>
                                <TableCell>{u.id}</TableCell><TableCell>{u.username}</TableCell>
                                <TableCell><Select value={u.role} size="small" sx={{ minWidth: 140 }}>{roles.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}</Select></TableCell>
                                <TableCell><StatusPill status={u.is_active ? "OK" : "OFFLINE"} /></TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </GlassCard>
        </Box>
    );
}
