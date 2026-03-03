import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useOutletContext } from "react-router-dom";
import { Box, Typography, Button, CircularProgress, TextField } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import GlassCard from "@/components/GlassCard";
import { fetchEmployees, type Employee } from "@/api/employees";
import { syncHikvisionUsers } from "@/api/devices";
import { fetchEsmoEmployees, syncEsmoEmployees, type EsmoEmployee } from "@/api/medical";
import { useAppTheme } from "@/context/ThemeContext";
import { employeeNoSearchHaystack, formatEmployeeNo } from "@/utils/employeeNo";

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
    const [turnstileSearch, setTurnstileSearch] = useState("");
    const [esmoSearch, setEsmoSearch] = useState("");

    const load = () => {
        setLoading(true);
        fetchEmployees()
            .then((empRows) => setEmployees(empRows))
            .catch(() => setEmployees([]))
            .finally(() => setLoading(false));
    };

    useEffect(() => { load(); }, []);
    useEffect(() => {
        setEsmoLoading(true);
        fetchEsmoEmployees()
            .then((rows) => setEsmoEmployees(rows))
            .catch(() => setEsmoEmployees([]))
            .finally(() => setEsmoLoading(false));
    }, []);

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

    const matchesTurnstileQuery = (e: Employee, query: string) => {
        const lowerQuery = query.trim().toLowerCase();
        if (!lowerQuery) return true;
        const fullName = `${e.last_name} ${e.first_name} ${e.patronymic || ""}`.toLowerCase();
        return (
            fullName.includes(lowerQuery) ||
            employeeNoSearchHaystack(e.employee_no).includes(lowerQuery) ||
            (e.department || "").toLowerCase().includes(lowerQuery) ||
            (e.position || "").toLowerCase().includes(lowerQuery)
        );
    };

    const matchesEsmoQuery = (e: EsmoEmployee, query: string) => {
        const lowerQuery = query.trim().toLowerCase();
        if (!lowerQuery) return true;
        return (
            employeeNoSearchHaystack(e.pass_id || "").includes(lowerQuery) ||
            String(e.full_name || "").toLowerCase().includes(lowerQuery) ||
            String(e.organization || "").toLowerCase().includes(lowerQuery) ||
            String(e.department || "").toLowerCase().includes(lowerQuery) ||
            String(e.position || "").toLowerCase().includes(lowerQuery)
        );
    };

    const filteredEmployees = employees.filter(
        (e) => matchesTurnstileQuery(e, searchQuery) && matchesTurnstileQuery(e, turnstileSearch)
    );

    const filteredEsmoEmployees = esmoEmployees.filter(
        (e) => matchesEsmoQuery(e, searchQuery) && matchesEsmoQuery(e, esmoSearch)
    );

    const columns: GridColDef[] = [
        {
            field: "employee_no",
            headerName: t("employees.col.employeeNo"),
            width: 150,
            hideable: false,
            valueGetter: (value) => formatEmployeeNo(value),
        },
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
        { field: "pass_id", headerName: t("employees.col.employeeNo"), width: 120, valueGetter: (value) => formatEmployeeNo(value) },
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

    const headerSearchSx = {
        minWidth: 180,
        maxWidth: 220,
        ml: 1,
        "& .MuiOutlinedInput-root": {
            bgcolor: "rgba(255, 255, 255, 0.05)",
        },
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
                        <TextField
                            size="small"
                            placeholder={t("events.search")}
                            value={turnstileSearch}
                            onChange={(e) => setTurnstileSearch(e.target.value)}
                            sx={headerSearchSx}
                        />
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
                        <TextField
                            size="small"
                            placeholder={t("events.search")}
                            value={esmoSearch}
                            onChange={(e) => setEsmoSearch(e.target.value)}
                            sx={headerSearchSx}
                        />
                    </Box>
                    <DataGrid
                        rows={filteredEsmoEmployees}
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
