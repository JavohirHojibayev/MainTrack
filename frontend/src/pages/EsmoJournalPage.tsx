import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, TextField, Button } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import DownloadIcon from "@mui/icons-material/DownloadRounded";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdfRounded";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { useAppTheme } from "@/context/ThemeContext";
import { fetchMedicalExams, type MedicalExam } from "@/api/medical";
import dayjs from "dayjs";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

const pageTitleGradientSx = {
    backgroundImage: "linear-gradient(45deg, #3b82f6 0%, #06b6d4 100%)",
    WebkitBackgroundClip: "text !important",
    backgroundClip: "text",
    WebkitTextFillColor: "transparent !important",
    color: "transparent !important",
    display: "inline-block",
};

type EsmoFilters = {
    start_date: string;
    end_date: string;
    search: string;
};

export default function EsmoJournalPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [rows, setRows] = useState<MedicalExam[]>([]);
    const [loading, setLoading] = useState(false);
    const [filters, setFilters] = useState<EsmoFilters>({
        start_date: "",
        end_date: "",
        search: "",
    });
    const [appliedFilters, setAppliedFilters] = useState<EsmoFilters>({
        start_date: "",
        end_date: "",
        search: "",
    });

    const loadExams = useCallback(async () => {
        setLoading(true);
        try {
            const data = await fetchMedicalExams({
                start_date: appliedFilters.start_date || undefined,
                end_date: appliedFilters.end_date || undefined,
                search: appliedFilters.search.trim() || undefined,
                limit: 5000,
            });
            setRows(data);
        } catch (err) {
            console.error("Failed to load exams", err);
        } finally {
            setLoading(false);
        }
    }, [appliedFilters]);

    useEffect(() => {
        loadExams();
    }, [loadExams]);
    useEffect(() => {
        const timer = window.setInterval(() => {
            loadExams();
        }, 10000);
        return () => window.clearInterval(timer);
    }, [loadExams]);

    const handleApply = () => {
        setAppliedFilters({
            start_date: filters.start_date,
            end_date: filters.end_date,
            search: filters.search.trim(),
        });
    };

    const toDisplayStatus = (statusRaw: string) => {
        const s = String(statusRaw || "").toLowerCase();
        if (s === "passed") return t("status.passed");
        if (s === "review" || s === "manual_review" || s === "ko'rik" || s === "korik") return t("status.review");
        if (s === "failed" || s === "fail" || s === "rejected") return t("status.failed");
        return statusRaw || "-";
    };
    const toColorStatus = (statusRaw: string) => {
        const s = String(statusRaw || "").toLowerCase();
        if (s === "passed") return "ACCEPTED";
        if (s === "review" || s === "manual_review") return "WARNING";
        if (s === "failed" || s === "fail" || s === "rejected") return "REJECTED";
        return "WARNING";
    };

    const columns: GridColDef<MedicalExam>[] = [
        {
            field: "full_name" as any,
            headerName: t("esmo.col.name") || "Name",
            width: 330,
            hideable: false,
            valueGetter: (_value, row) => {
                const emp = row.employee;
                return emp ? [emp.last_name, emp.first_name, emp.patronymic].filter(Boolean).join(" ") : `ID: ${row.employee_id}`;
            }
        },
        {
            field: "timestamp",
            headerName: t("esmo.col.time") || "Time",
            width: 180,
            hideable: false,
            valueFormatter: (value) => dayjs(value).format("DD.MM.YYYY HH:mm")
        },
        {
            field: "terminal_name",
            headerName: t("esmo.col.device") || "Device",
            width: 220,
            hideable: false
        },
        {
            field: "pressure" as any,
            headerName: t("esmo.col.pressure") || "Pressure",
            width: 120,
            valueGetter: (_value, row) => {
                if (row.pressure_systolic == null || row.pressure_diastolic == null) return "-";
                return `${row.pressure_systolic}/${row.pressure_diastolic}`;
            }
        },
        {
            field: "pulse",
            headerName: t("esmo.col.pulse") || "Pulse",
            width: 100
        },
        {
            field: "temperature",
            headerName: t("esmo.col.temperature") || "Temp",
            width: 100,
            valueFormatter: (value) => (value == null ? "-" : `${value}\u00B0C`)
        },
        {
            field: "result",
            headerName: t("esmo.col.status") || "Status",
            width: 130,
            hideable: false,
            renderCell: (p) => {
                const rawStatus = String(p.value ?? "");
                const shownStatus = toDisplayStatus(rawStatus);
                const colorStatus = toColorStatus(rawStatus);
                return <StatusPill status={shownStatus} colorStatus={colorStatus} />;
            }
        },
    ];

    const getFullName = (row: MedicalExam) => {
        const emp = row.employee;
        return emp ? [emp.last_name, emp.first_name, emp.patronymic].filter(Boolean).join(" ") : `ID: ${row.employee_id}`;
    };

    const formatTime = (ts: string) => dayjs(ts).format("DD.MM.YYYY HH:mm");
    const formatPressure = (row: MedicalExam) =>
        row.pressure_systolic == null || row.pressure_diastolic == null
            ? "-"
            : `${row.pressure_systolic}/${row.pressure_diastolic}`;
    const formatPulse = (pulse?: number) => (pulse == null ? "-" : String(pulse));
    const formatTemperature = (temperature?: number) => (temperature == null ? "-" : `${temperature}\u00B0C`);

    const exportCSV = () => {
        if (rows.length === 0) return;
        const header = `${t("esmo.col.name")};${t("esmo.col.time")};${t("esmo.col.device")};${t("esmo.col.pressure")};${t("esmo.col.pulse")};${t("esmo.col.temperature")};${t("esmo.col.status")}\n`;
        const csvRows = rows.map((r) =>
            `"${getFullName(r)}";"${formatTime(r.timestamp)}";"${r.terminal_name || "-"}";"${formatPressure(r)}";"${formatPulse(r.pulse)}";"${formatTemperature(r.temperature)}";"${toDisplayStatus(String(r.result ?? ""))}"`
        ).join("\n");

        const blob = new Blob(["\uFEFF" + header + csvRows], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `esmo_journal_${new Date().toISOString().split("T")[0]}.csv`);
        link.click();
    };

    const exportPDF = async () => {
        if (rows.length === 0) return;
        const doc = new jsPDF({ orientation: "landscape" });

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
        doc.text(t("esmo.title"), 14, 18);
        doc.setFontSize(10);
        doc.setTextColor(100);
        doc.text(`${t("events.generated")}: ${new Date().toLocaleString()}`, 14, 25);

        const tableData = rows.map((r) => [
            getFullName(r),
            formatTime(r.timestamp),
            r.terminal_name || "-",
            formatPressure(r),
            formatPulse(r.pulse),
            formatTemperature(r.temperature),
            toDisplayStatus(String(r.result ?? "")),
        ]);

        autoTable(doc, {
            head: [[
                t("esmo.col.name"),
                t("esmo.col.time"),
                t("esmo.col.device"),
                t("esmo.col.pressure"),
                t("esmo.col.pulse"),
                t("esmo.col.temperature"),
                t("esmo.col.status"),
            ]],
            body: tableData,
            startY: 30,
            theme: "grid",
            headStyles: { fillColor: [59, 130, 246], font: "Roboto" },
            styles: { fontSize: 9, font: "Roboto" },
            columnStyles: { 0: { cellWidth: 55 }, 2: { cellWidth: 52 } },
        });

        doc.save(`esmo_journal_${new Date().toISOString().split("T")[0]}.pdf`);
    };

    return (
        <Box sx={{ height: "calc(100vh - 120px)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <Typography variant="h4" sx={{
                mb: 3,
                fontSize: "2.5rem",
                fontWeight: 700,
                flexShrink: 0
            }}>
                <Box component="span" sx={pageTitleGradientSx}>{t("esmo.title")}</Box>
            </Typography>
            <Box sx={{ mb: 4, display: "flex", gap: 2, alignItems: "center", flexWrap: "nowrap", flexShrink: 0 }}>
                <TextField
                    label={t("esmo.dateFrom")}
                    type="date"
                    value={filters.start_date}
                    onChange={(e) => setFilters((f) => ({ ...f, start_date: e.target.value }))}
                    InputLabelProps={{ shrink: true }}
                    sx={{ minWidth: 160 }}
                />
                <TextField
                    label={t("esmo.dateTo")}
                    type="date"
                    value={filters.end_date}
                    onChange={(e) => setFilters((f) => ({ ...f, end_date: e.target.value }))}
                    InputLabelProps={{ shrink: true }}
                    sx={{ minWidth: 160 }}
                />
                <TextField
                    label={t("esmo.search")}
                    placeholder={t("esmo.searchHint")}
                    value={filters.search}
                    onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
                    onKeyDown={(e) => {
                        if (e.key === "Enter") handleApply();
                    }}
                    sx={{ minWidth: 200 }}
                />
                <Button
                    variant="contained"
                    onClick={handleApply}
                    sx={{ height: 40, minWidth: 100, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap" }}
                >
                    {t("esmo.apply")}
                </Button>
                <Button
                    variant="contained"
                    startIcon={<DownloadIcon />}
                    onClick={exportCSV}
                    disabled={rows.length === 0 || loading}
                    sx={{ height: 40, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap", background: "linear-gradient(135deg, #06b6d4, #3b82f6)", "&:hover": { background: "linear-gradient(135deg, #0891b2, #2563eb)" } }}
                >
                    {t("esmo.exportCsv")}
                </Button>
                <Button
                    variant="contained"
                    startIcon={<PictureAsPdfIcon />}
                    onClick={exportPDF}
                    disabled={rows.length === 0 || loading}
                    sx={{ height: 40, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap", background: "linear-gradient(135deg, #06b6d4, #3b82f6)", "&:hover": { background: "linear-gradient(135deg, #0891b2, #2563eb)" } }}
                >
                    {t("esmo.exportPdf")}
                </Button>
            </Box>
            <GlassCard sx={{ p: 0, flex: 1, width: "fit-content", minWidth: 1180, overflow: "hidden", "& .MuiDataGrid-root": { border: "none" } }}>
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
