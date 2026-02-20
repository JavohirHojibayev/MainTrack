import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, TextField, Button } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import DownloadIcon from "@mui/icons-material/DownloadRounded";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdfRounded";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { useAppTheme } from "@/context/ThemeContext";

interface EsmoRow {
    id: number;
    full_name: string;
    employee_no: string;
    event_ts: string;
    device_name: string;
    status: string;
    result: string;
}

export default function EsmoJournalPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [rows] = useState<EsmoRow[]>([]);
    const [loading] = useState(false);

    const columns: GridColDef[] = [
        { field: "full_name", headerName: t("esmo.col.name") || "Name", width: 300, hideable: false },
        { field: "employee_no", headerName: t("esmo.col.employeeNo") || "Employee #", width: 160, hideable: false },
        { field: "event_ts", headerName: t("esmo.col.time") || "Time", width: 220, hideable: false },
        { field: "device_name", headerName: t("esmo.col.device") || "Device", width: 190, hideable: false },
        {
            field: "status",
            headerName: t("esmo.col.status") || "Status",
            width: 130,
            hideable: false,
            renderCell: (p) => <StatusPill status={p.value} />
        },
    ];

    return (
        <Box sx={{ height: "calc(100vh - 120px)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <Typography variant="h4" sx={{
                mb: 3,
                fontSize: "2.5rem",
                fontWeight: 700,
                background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                display: "inline-block",
                flexShrink: 0
            }}>{t("esmo.title")}</Typography>
            <Box sx={{ mb: 4, display: "flex", gap: 2, alignItems: "center", flexWrap: "nowrap", flexShrink: 0 }}>
                <TextField label={t("esmo.dateFrom")} type="date" InputLabelProps={{ shrink: true }} sx={{ minWidth: 160 }} />
                <TextField label={t("esmo.dateTo")} type="date" InputLabelProps={{ shrink: true }} sx={{ minWidth: 160 }} />
                <TextField label={t("esmo.search")} placeholder={t("esmo.searchHint")} sx={{ minWidth: 200 }} />
                <Button variant="contained" sx={{ height: 40, minWidth: 100, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap" }}>{t("esmo.apply")}</Button>
                <Button
                    variant="contained"
                    startIcon={<DownloadIcon />}
                    disabled={rows.length === 0 || loading}
                    sx={{ height: 40, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap", background: "linear-gradient(135deg, #06b6d4, #3b82f6)", "&:hover": { background: "linear-gradient(135deg, #0891b2, #2563eb)" } }}
                >
                    {t("esmo.exportCsv")}
                </Button>
                <Button
                    variant="contained"
                    startIcon={<PictureAsPdfIcon />}
                    disabled={rows.length === 0 || loading}
                    sx={{ height: 40, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap", background: "linear-gradient(135deg, #06b6d4, #3b82f6)", "&:hover": { background: "linear-gradient(135deg, #0891b2, #2563eb)" } }}
                >
                    {t("esmo.exportPdf")}
                </Button>
            </Box>
            <GlassCard sx={{ p: 0, flex: 1, width: "fit-content", minWidth: 1020, overflow: "hidden", "& .MuiDataGrid-root": { border: "none" } }}>
                <DataGrid
                    rows={rows} columns={columns} loading={loading}
                    pageSizeOptions={[25, 50, 100]}
                    initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
                    disableColumnSorting
                    disableColumnMenu
                    sx={{
                        height: "100%",
                        width: "100%",
                        "& .MuiDataGrid-columnHeaders": { bgcolor: tokens.bg.tableHeader },
                        "& .MuiDataGrid-row:nth-of-type(even)": { bgcolor: tokens.bg.tableRowAlt },
                        "& .MuiDataGrid-cell": { borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" },
                    }}
                />
            </GlassCard>
        </Box>
    );
}
