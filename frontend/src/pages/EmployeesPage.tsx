import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useOutletContext } from "react-router-dom";
import { Box, Typography, Button, CircularProgress } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import GlassCard from "@/components/GlassCard";
import { fetchEmployees, type Employee } from "@/api/employees";
import { syncHikvisionUsers } from "@/api/devices";
import { fetchEsmoEmployees, syncEsmoEmployees, type EsmoEmployee } from "@/api/medical";
import { useAppTheme } from "@/context/ThemeContext";

export default function EmployeesPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const { searchQuery } = useOutletContext<{ searchQuery: string }>();
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [esmoEmployees, setEsmoEmployees] = useState<EsmoEmployee[]>([]);
    const [loading, setLoading] = useState(false);
    const [esmoLoading, setEsmoLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [esmoSyncing, setEsmoSyncing] = useState(false);

    const withTimeout = <T,>(promise: Promise<T>, ms: number): Promise<T> =>
        new Promise((resolve, reject) => {
            const timer = window.setTimeout(() => reject(new Error("timeout")), ms);
            promise
                .then((value) => {
                    window.clearTimeout(timer);
                    resolve(value);
                })
                .catch((err) => {
                    window.clearTimeout(timer);
                    reject(err);
                });
        });

    const loadEsmo = () => {
        setEsmoLoading(true);
        withTimeout(fetchEsmoEmployees(), 120000)
            .then((esmoRows) => setEsmoEmployees(esmoRows))
            .catch(() => { })
            .finally(() => setEsmoLoading(false));
    };

    const load = () => {
        setLoading(true);
        fetchEmployees()
            .then((empRows) => setEmployees(empRows))
            .catch(() => setEmployees([]))
            .finally(() => setLoading(false));
        loadEsmo();
    };

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

    const handleEsmoSync = async () => {
        setEsmoSyncing(true);
        try {
            const res = await syncEsmoEmployees();
            setEsmoEmployees(res);
            alert("ESMO Employees synced successfully");
        } catch (e) {
            console.error(e);
            alert("ESMO Sync error");
        } finally {
            setEsmoSyncing(false);
        }
    };

    const filteredEmployees = employees.filter(e => {
        if (!searchQuery) return true;
        const lowerQuery = searchQuery.toLowerCase();
        const fullName = `${e.last_name} ${e.first_name} ${e.patronymic || ""}`.toLowerCase();
        return fullName.includes(lowerQuery) || e.employee_no.toLowerCase().includes(lowerQuery);
    });

    const columns: GridColDef[] = [
        { field: "employee_no", headerName: t("employees.col.employeeNo"), width: 150, hideable: false },
        {
            field: "full_name",
            headerName: t("employees.col.fullName"),
            flex: 1,
            minWidth: 200,
            hideable: false,
            valueGetter: (value, row) => {
                const parts = [row.last_name, row.first_name, row.patronymic].filter(Boolean);
                return parts.join(" ");
            }
        }
    ];

    const esmoColumns: GridColDef[] = [
        { field: "pass_id", headerName: t("employees.col.employeeNo"), width: 120 },
        { field: "full_name", headerName: t("employees.col.fullName"), flex: 1, minWidth: 200 },
        { field: "organization", headerName: "Org", width: 150 },
        { field: "department", headerName: "Dept", width: 150 },
        { field: "position", headerName: "Pos", width: 200 },
    ];

    const syncButtonSx = {
        borderRadius: "20px",
        textTransform: "none" as const,
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
    };

    const dataGridSx = {
        flex: 1,
        width: "100%",
        minHeight: 0,
        "& .MuiDataGrid-columnHeaders": { bgcolor: tokens.bg.tableHeader },
        "& .MuiDataGrid-row:nth-of-type(even)": { bgcolor: tokens.bg.tableRowAlt },
        "& .MuiDataGrid-cell": { borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" },
    };

    return (
        <Box sx={{ height: "calc(100vh - 120px)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <Box sx={{ mb: 3, flexShrink: 0 }}>
                <Typography variant="h4" sx={{
                    fontSize: "2.5rem",
                    fontWeight: 700,
                    background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    display: "inline-block",
                }}>{t("employees.title")}</Typography>
            </Box>

            <Box sx={{ display: "flex", gap: 2, flex: 1, minHeight: 0 }}>
                {/* Turniket Table */}
                <GlassCard sx={{ p: 0, display: "flex", flexDirection: "column", flex: 0.85, minWidth: 0, overflow: "hidden", "& .MuiDataGrid-root": { border: "none" } }}>
                    <Box sx={{ p: 2, display: "flex", alignItems: "center", gap: 2, bgcolor: tokens.mode === "dark" ? tokens.bg.tableHeader : "#F0F4FA" }}>
                        <Typography variant="h4" sx={{ fontWeight: 700, fontSize: "30px", color: "#1976d2" }}>Turniket</Typography>
                        <Button
                            variant="outlined"
                            onClick={handleSync}
                            disabled={syncing}
                            size="small"
                            sx={syncButtonSx}
                            startIcon={syncing ? <CircularProgress size={16} /> : null}
                        >
                            {syncing ? t("employees.syncing") : t("employees.syncButton")}
                        </Button>
                    </Box>
                    <DataGrid
                        rows={filteredEmployees}
                        columns={columns}
                        loading={loading}
                        disableColumnSorting
                        disableColumnMenu
                        pageSizeOptions={[25, 50, 100]}
                        initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
                        sx={dataGridSx}
                    />
                </GlassCard>

                {/* ESMO Table */}
                <GlassCard sx={{ p: 0, display: "flex", flexDirection: "column", flex: 1.15, minWidth: 0, overflow: "hidden", "& .MuiDataGrid-root": { border: "none" } }}>
                    <Box sx={{ p: 2, display: "flex", alignItems: "center", gap: 2, bgcolor: tokens.mode === "dark" ? tokens.bg.tableHeader : "#F0F4FA" }}>
                        <Typography variant="h4" sx={{ fontWeight: 700, fontSize: "30px", color: "#1976d2" }}>ESMO</Typography>
                        <Button
                            variant="outlined"
                            onClick={handleEsmoSync}
                            disabled={esmoSyncing}
                            size="small"
                            sx={syncButtonSx}
                            startIcon={esmoSyncing ? <CircularProgress size={16} /> : null}
                        >
                            {esmoSyncing ? t("employees.esmoSyncing") : t("employees.esmoSyncButton")}
                        </Button>
                    </Box>
                    <DataGrid
                        rows={esmoEmployees}
                        columns={esmoColumns}
                        loading={esmoLoading}
                        disableColumnSorting
                        disableColumnMenu
                        pageSizeOptions={[25, 50, 100]}
                        initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
                        sx={dataGridSx}
                    />
                </GlassCard>
            </Box>
        </Box>
    );
}
