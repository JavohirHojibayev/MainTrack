import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, Button, Table, TableBody, TableCell, TableHead, TableRow, CircularProgress } from "@mui/material";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { fetchEmployees, type Employee } from "@/api/employees";
import { syncHikvisionUsers } from "@/api/devices";
import { useAppTheme } from "@/context/ThemeContext";

export default function EmployeesPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [syncing, setSyncing] = useState(false);

    const load = () => { fetchEmployees().then(setEmployees).catch(() => { }); };
    useEffect(() => { load(); }, []);

    const handleSync = async () => {
        setSyncing(true);
        try {
            const res = await syncHikvisionUsers();
            if (res.success) {
                alert(res.message);
                load();
            } else {
                alert("Sync failed: " + res.message);
            }
        } catch (e) {
            console.error(e);
            alert("Sync error");
        } finally {
            setSyncing(false);
        }
    };

    return (
        <Box sx={{ p: 2 }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
                <Typography variant="h4" sx={{
                    fontSize: "2.5rem",
                    fontWeight: 700,
                    background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    display: "inline-block"
                }}>{t("employees.title")}</Typography>
                <Button
                    variant="outlined"
                    onClick={handleSync}
                    disabled={syncing}
                    startIcon={syncing ? <CircularProgress size={20} /> : null}
                >
                    {syncing ? "Syncing..." : "Sync from Turnstile"}
                </Button>
            </Box>

            <GlassCard sx={{ width: "fit-content", minWidth: 650 }}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell sx={{ width: "120px" }}>{t("employees.col.employeeNo")}</TableCell>
                            <TableCell sx={{ width: "350px" }}>{t("employees.col.fullName")}</TableCell>
                            <TableCell sx={{ width: "100px", textAlign: "center" }}>{t("employees.col.status")}</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {employees.map((e) => (
                            <TableRow key={e.id}>
                                <TableCell>{e.employee_no}</TableCell>
                                <TableCell>{`${e.last_name} ${e.first_name} ${e.patronymic || ""}`.trim()}</TableCell>
                                <TableCell sx={{ textAlign: "center" }}><StatusPill status={e.is_active ? "OK" : "OFFLINE"} /></TableCell>
                            </TableRow>
                        ))}
                        {employees.length === 0 && <TableRow><TableCell colSpan={3} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("employees.noEmployees")}</TableCell></TableRow>}
                    </TableBody>
                </Table>
            </GlassCard>
        </Box>
    );
}
