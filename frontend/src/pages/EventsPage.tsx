import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, TextField, MenuItem, Button, Grid, Drawer, IconButton } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import CloseIcon from "@mui/icons-material/CloseRounded";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { fetchEvents, type EventRow, type EventFilters } from "@/api/events";
import { useAppTheme } from "@/context/ThemeContext";

const eventTypes = ["", "TURNSTILE_IN", "TURNSTILE_OUT", "ESMO_OK", "ESMO_FAIL", "TOOL_TAKE", "TOOL_RETURN", "MINE_IN", "MINE_OUT"];
const statuses = ["", "ACCEPTED", "REJECTED"];

export default function EventsPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [rows, setRows] = useState<EventRow[]>([]);
    const [loading, setLoading] = useState(false);
    const [filters, setFilters] = useState<EventFilters>({});
    const [selected, setSelected] = useState<EventRow | null>(null);

    const columns: GridColDef[] = [
        {
            field: "full_name",
            headerName: t("events.col.name") || "Name",
            width: 200,
            hideable: false,
            valueGetter: (value, row) => {
                if (row && row.first_name && row.last_name) return `${row.last_name} ${row.first_name}`;
                return "";
            }
        },
        { field: "employee_no", headerName: t("events.col.employeeNo") || "Employee #", width: 120, hideable: false },
        { field: "event_ts", headerName: t("events.col.time"), width: 180, hideable: false, valueFormatter: (p) => { try { return new Date(p as string).toLocaleString("en-GB"); } catch { return p as string; } } },
        { field: "event_type", headerName: t("events.col.type"), width: 140, hideable: false },
        { field: "device_id", headerName: t("events.col.deviceId"), width: 100, hideable: false },
        {
            field: "status",
            headerName: t("events.col.status"),
            width: 130,
            hideable: false,
            renderCell: (p) => {
                const isMineIn = p.row.event_type === "MINE_IN";
                const colorStatus = isMineIn && p.value === "ACCEPTED" ? "WARNING" : undefined;
                return <StatusPill status={p.value} colorStatus={colorStatus} />;
            }
        },
        { field: "reject_reason", headerName: t("events.col.reason"), flex: 1, hideable: false },
    ];

    const load = () => { setLoading(true); fetchEvents(filters).then(setRows).catch(() => { }).finally(() => setLoading(false)); };
    useEffect(() => { load(); }, []);

    return (
        <Box>
            <Typography variant="h4" sx={{
                mb: 3,
                fontSize: "2.5rem",
                fontWeight: 700,
                background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                display: "inline-block"
            }}>{t("events.title")}</Typography>
            <GlassCard sx={{ mb: 3, p: 2 }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} sm={6} md={2}><TextField label={t("events.dateFrom")} type="datetime-local" fullWidth InputLabelProps={{ shrink: true }} onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value ? new Date(e.target.value).toISOString() : undefined }))} /></Grid>
                    <Grid item xs={12} sm={6} md={2}><TextField label={t("events.dateTo")} type="datetime-local" fullWidth InputLabelProps={{ shrink: true }} onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value ? new Date(e.target.value).toISOString() : undefined }))} /></Grid>
                    <Grid item xs={12} sm={6} md={2}><TextField label={t("events.employeeNo")} fullWidth onChange={(e) => setFilters((f) => ({ ...f, employee_no: e.target.value || undefined }))} /></Grid>
                    <Grid item xs={12} sm={6} md={2}>
                        <TextField label={t("events.eventType")} select fullWidth value={filters.event_type ?? ""} onChange={(e) => setFilters((f) => ({ ...f, event_type: e.target.value || undefined }))}>
                            {eventTypes.map((v) => <MenuItem key={v} value={v}>{v || t("events.all")}</MenuItem>)}
                        </TextField>
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                        <TextField label={t("events.status")} select fullWidth value={filters.status ?? ""} onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value || undefined }))}>
                            {statuses.map((v) => <MenuItem key={v} value={v}>{v || t("events.all")}</MenuItem>)}
                        </TextField>
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}><Button variant="contained" fullWidth onClick={load} sx={{ height: 40 }}>{t("events.apply")}</Button></Grid>
                </Grid>
            </GlassCard>
            <GlassCard sx={{ p: 0, "& .MuiDataGrid-root": { border: "none" } }}>
                <DataGrid
                    rows={rows} columns={columns} loading={loading}
                    pageSizeOptions={[25, 50, 100]}
                    initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
                    onRowClick={(p) => setSelected(p.row as EventRow)}
                    autoHeight
                    sx={{
                        "& .MuiDataGrid-columnHeaders": { bgcolor: tokens.bg.tableHeader },
                        "& .MuiDataGrid-row:nth-of-type(even)": { bgcolor: tokens.bg.tableRowAlt },
                        "& .MuiDataGrid-cell": { borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" },
                    }}
                />
            </GlassCard>
            <Drawer anchor="right" open={!!selected} onClose={() => setSelected(null)}>
                <Box sx={{ width: 400, p: 3 }}>
                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 3 }}>
                        <Typography variant="h6">{t("events.details")}</Typography>
                        <IconButton onClick={() => setSelected(null)}><CloseIcon /></IconButton>
                    </Box>
                    {selected && (
                        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                            <Typography variant="body2"><strong>{t("events.id")}:</strong> {selected.id}</Typography>
                            <Typography variant="body2"><strong>{t("events.col.time")}:</strong> {new Date(selected.event_ts).toLocaleString()}</Typography>
                            <Typography variant="body2"><strong>{t("events.col.type")}:</strong> {selected.event_type}</Typography>
                            <Typography variant="body2"><strong>{t("events.employeeId")}:</strong> {selected.employee_id}</Typography>
                            <Typography variant="body2"><strong>{t("events.deviceId")}:</strong> {selected.device_id}</Typography>
                            <Box><strong>{t("events.col.status")}:</strong> <StatusPill status={selected.status} /></Box>
                            {selected.reject_reason && <Typography variant="body2" sx={{ color: tokens.status.blocked }}><strong>{t("events.col.reason")}:</strong> {selected.reject_reason}</Typography>}
                            <Typography variant="body2"><strong>{t("events.rawId")}:</strong> {selected.raw_id}</Typography>
                        </Box>
                    )}
                </Box>
            </Drawer>
        </Box>
    );
}
