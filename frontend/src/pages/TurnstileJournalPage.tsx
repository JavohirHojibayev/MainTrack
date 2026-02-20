import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, TextField, Button, Grid, Drawer, IconButton } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import CloseIcon from "@mui/icons-material/CloseRounded";
import DownloadIcon from "@mui/icons-material/DownloadRounded";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdfRounded";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { fetchEvents, type EventRow, type EventFilters } from "@/api/events";
import { useAppTheme } from "@/context/ThemeContext";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

export default function TurnstileJournalPage() {
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
            width: 300,
            hideable: false,
            valueGetter: (value, row) => {
                const parts = [row.last_name, row.first_name, row.patronymic].filter(Boolean);
                return parts.join(" ");
            }
        },
        { field: "employee_no", headerName: t("events.col.employeeNo") || "Employee #", width: 160, hideable: false },
        { field: "event_ts", headerName: t("events.col.time"), width: 220, hideable: false, valueFormatter: (p) => { try { return new Date(p as string).toLocaleString("en-GB"); } catch { return p as string; } } },
        {
            field: "device_name",
            headerName: t("events.col.deviceId") || "Device",
            width: 190,
            hideable: false,
            valueGetter: (value, row) => row.device_name || row.device_id
        },
        {
            field: "status",
            headerName: t("events.col.status"),
            width: 130,
            hideable: false,
            renderCell: (p) => {
                const isEntry = p.row.event_type === "TURNSTILE_IN" || p.row.event_type === "MINE_IN";
                return <StatusPill status={p.value} colorStatus={isEntry ? "WARNING" : undefined} />;
            }
        },
    ];

    const getFullName = (row: EventRow) => [row.last_name, row.first_name, row.patronymic].filter(Boolean).join(" ");
    const formatTime = (ts: string) => { try { return new Date(ts).toLocaleString("en-GB"); } catch { return ts; } };

    const exportCSV = () => {
        if (rows.length === 0) return;
        const header = `${t("events.col.name")};${t("events.col.employeeNo")};${t("events.col.time")};${t("events.col.deviceId")};${t("events.col.status")}\n`;
        const csvRows = rows.map(r =>
            `"${getFullName(r)}";"${r.employee_no || ""}";"${formatTime(r.event_ts)}";"${r.device_name || r.device_id}";"${r.status}"`
        ).join("\n");
        const blob = new Blob(["\uFEFF" + header + csvRows], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `turnstile_journal_${new Date().toISOString().split('T')[0]}.csv`);
        link.click();
    };

    const exportPDF = async () => {
        if (rows.length === 0) return;
        const doc = new jsPDF({ orientation: "landscape" });

        // Load Roboto font for Cyrillic support
        try {
            const fontRes = await fetch("https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.2.7/fonts/Roboto/Roboto-Regular.ttf");
            const buf = await fontRes.arrayBuffer();
            const bytes = new Uint8Array(buf);
            let binary = "";
            for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
            const base64 = btoa(binary);
            doc.addFileToVFS("Roboto.ttf", base64);
            doc.addFont("Roboto.ttf", "Roboto", "normal");
            doc.setFont("Roboto");
        } catch { /* fallback to default font */ }

        doc.setFontSize(16);
        doc.text(t("events.title"), 14, 18);
        doc.setFontSize(10);
        doc.setTextColor(100);
        doc.text(`${t("events.generated")}: ${new Date().toLocaleString()}`, 14, 25);

        const tableData = rows.map(r => [
            getFullName(r),
            r.employee_no || "",
            formatTime(r.event_ts),
            r.device_name || String(r.device_id),
            r.status,
        ]);

        autoTable(doc, {
            head: [[t("events.col.name"), t("events.col.employeeNo"), t("events.col.time"), t("events.col.deviceId"), t("events.col.status")]],
            body: tableData,
            startY: 30,
            theme: "grid",
            headStyles: { fillColor: [59, 130, 246], font: "Roboto" },
            styles: { fontSize: 9, font: "Roboto" },
            columnStyles: { 0: { cellWidth: 80 } },
        });

        doc.save(`turnstile_journal_${new Date().toISOString().split('T')[0]}.pdf`);
    };

    const load = () => { setLoading(true); fetchEvents(filters).then(setRows).catch(() => { }).finally(() => setLoading(false)); };
    useEffect(() => { load(); }, []);

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
            }}>{t("events.title")}</Typography>
            <Box sx={{ mb: 4, display: "flex", gap: 2, alignItems: "center", flexWrap: "nowrap", flexShrink: 0 }}>
                <TextField label={t("events.dateFrom")} type="date" InputLabelProps={{ shrink: true }} sx={{ minWidth: 160 }} onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value ? new Date(e.target.value).toISOString() : undefined }))} />
                <TextField label={t("events.dateTo")} type="date" InputLabelProps={{ shrink: true }} sx={{ minWidth: 160 }} onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value ? new Date(e.target.value + "T23:59:59").toISOString() : undefined }))} />
                <TextField label={t("events.search")} placeholder={t("events.searchHint")} sx={{ minWidth: 200 }} onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))} />
                <Button variant="contained" onClick={load} sx={{ height: 40, minWidth: 100, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap" }}>{t("events.apply")}</Button>
                <Button
                    variant="contained"
                    startIcon={<DownloadIcon />}
                    onClick={exportCSV}
                    disabled={rows.length === 0 || loading}
                    sx={{ height: 40, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap", background: "linear-gradient(135deg, #06b6d4, #3b82f6)", "&:hover": { background: "linear-gradient(135deg, #0891b2, #2563eb)" } }}
                >
                    {t("events.exportCsv")}
                </Button>
                <Button
                    variant="contained"
                    startIcon={<PictureAsPdfIcon />}
                    onClick={exportPDF}
                    disabled={rows.length === 0 || loading}
                    sx={{ height: 40, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap", background: "linear-gradient(135deg, #06b6d4, #3b82f6)", "&:hover": { background: "linear-gradient(135deg, #0891b2, #2563eb)" } }}
                >
                    {t("events.exportPdf")}
                </Button>
            </Box>
            <GlassCard sx={{ p: 0, flex: 1, width: "fit-content", minWidth: 1020, overflow: "hidden", "& .MuiDataGrid-root": { border: "none" } }}>
                <DataGrid
                    rows={rows} columns={columns} loading={loading}
                    pageSizeOptions={[25, 50, 100]}
                    initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
                    onRowClick={(p) => setSelected(p.row as EventRow)}
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
