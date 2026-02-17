import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useOutletContext } from "react-router-dom";
import { Box, Typography, Button, Table, TableBody, TableCell, TableHead, TableRow, TablePagination, CircularProgress } from "@mui/material";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { fetchEmployees, type Employee } from "@/api/employees";
import { syncHikvisionUsers } from "@/api/devices";
import { useAppTheme } from "@/context/ThemeContext";

export default function EmployeesPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const { searchQuery } = useOutletContext<{ searchQuery: string }>();
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [syncing, setSyncing] = useState(false);
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(25);

    const filteredEmployees = employees.filter(e => {
        if (!searchQuery) return true;
        const lowerQuery = searchQuery.toLowerCase();
        const fullName = `${e.last_name} ${e.first_name} ${e.patronymic || ""}`.toLowerCase();
        return fullName.includes(lowerQuery) || e.employee_no.toLowerCase().includes(lowerQuery);
    });

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
            </Box>
            <GlassCard sx={{ width: "fit-content", minWidth: 650 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
                    <Typography variant="h4" sx={{ fontWeight: 700, px: 1, fontSize: "30px", color: "#1976d2" }}>Turniket</Typography>
                    <Button
                        variant="outlined"
                        onClick={handleSync}
                        disabled={syncing}
                        size="small"
                        sx={{
                            borderRadius: "20px",
                            textTransform: "none",
                            fontSize: "14px",
                            fontWeight: 600,
                            height: "32px",
                            color: "#3b82f6",
                            borderColor: "#3b82f6",
                            bgcolor: "rgba(59, 130, 246, 0.05)",
                            "&:hover": {
                                bgcolor: "rgba(59, 130, 246, 0.1)",
                                borderColor: "#3b82f6"
                            }
                        }}
                        startIcon={syncing ? <CircularProgress size={16} /> : null}
                    >
                        {syncing ? "Syncing..." : "Sync from Turnstile"}
                    </Button>
                </Box>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell sx={{ width: "120px" }}>{t("employees.col.employeeNo")}</TableCell>
                            <TableCell sx={{ width: "350px" }}>{t("employees.col.fullName")}</TableCell>
                            <TableCell sx={{ width: "100px", textAlign: "center" }}>{t("employees.col.status")}</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {filteredEmployees
                            .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                            .map((e) => (
                                <TableRow key={e.id}>
                                    <TableCell>{e.employee_no}</TableCell>
                                    <TableCell>{`${e.last_name} ${e.first_name} ${e.patronymic || ""}`.trim()}</TableCell>
                                    <TableCell sx={{ textAlign: "center" }}><StatusPill status={e.is_active ? "OK" : "OFFLINE"} /></TableCell>
                                </TableRow>
                            ))}
                        {filteredEmployees.length === 0 && <TableRow><TableCell colSpan={3} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("employees.noEmployees")}</TableCell></TableRow>}
                    </TableBody>
                </Table>
                <TablePagination
                    rowsPerPageOptions={[25, 50, 100]}
                    component="div"
                    count={filteredEmployees.length}
                    rowsPerPage={rowsPerPage}
                    page={page}
                    onPageChange={(e, newPage) => setPage(newPage)}
                    onRowsPerPageChange={(e) => {
                        setRowsPerPage(parseInt(e.target.value, 10));
                        setPage(0);
                    }}
                />
            </GlassCard>
        </Box>
    );
}
