import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useOutletContext } from "react-router-dom";
import { Box, Typography, Button, CircularProgress } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
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
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);

    const load = () => {
        setLoading(true);
        fetchEmployees()
            .then(setEmployees)
            .catch(() => { })
            .finally(() => setLoading(false));
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
            width: 400,
            hideable: false,
            valueGetter: (value, row) => {
                const parts = [row.last_name, row.first_name, row.patronymic].filter(Boolean);
                return parts.join(" ");
            }
        },
        {
            field: "status",
            headerName: t("employees.col.status"),
            width: 150,
            headerAlign: "center",
            align: "center",
            hideable: false,
            renderCell: (params) => <StatusPill status={params.row.is_active ? "OK" : "OFFLINE"} />
        },
    ];

    return (
        <Box sx={{ height: "calc(100vh - 120px)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <Box sx={{ mb: 3, flexShrink: 0 }}>
                <Typography variant="h4" sx={{
                    fontSize: "2.5rem",
                    fontWeight: 700,
                    background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                }}>{t("employees.title")}</Typography>
            </Box>

            <GlassCard sx={{ p: 0, display: "flex", flexDirection: "column", flex: 1, width: "fit-content", minWidth: 0, maxWidth: "100%", overflow: "hidden", "& .MuiDataGrid-root": { border: "none" } }}>
                <Box sx={{ p: 2, display: "flex", alignItems: "center", gap: 2, bgcolor: tokens.mode === "dark" ? tokens.bg.tableHeader : "#F0F4FA" }}>
                    <Typography variant="h4" sx={{ fontWeight: 700, fontSize: "30px", color: "#1976d2" }}>Turniket</Typography>
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
                    sx={{
                        flex: 1,
                        width: "100%",
                        minHeight: 0,
                        "& .MuiDataGrid-columnHeaders": { bgcolor: tokens.bg.tableHeader },
                        "& .MuiDataGrid-row:nth-of-type(even)": { bgcolor: tokens.bg.tableRowAlt },
                        "& .MuiDataGrid-cell": { borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" },
                    }}
                />
            </GlassCard>
        </Box>
    );
}
