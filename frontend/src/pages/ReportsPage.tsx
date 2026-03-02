import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
    Box,
    Typography,
    TextField,
    Button,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableRow,
    TableContainer,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/DownloadRounded";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdfRounded";
import LoginIcon from "@mui/icons-material/LoginRounded";
import LogoutIcon from "@mui/icons-material/LogoutRounded";
import MedicalServicesIcon from "@mui/icons-material/MedicalServicesRounded";
import ReportProblemIcon from "@mui/icons-material/ReportProblemRounded";
import BuildIcon from "@mui/icons-material/BuildRounded";
import HandymanIcon from "@mui/icons-material/HandymanRounded";
import SensorDoorIcon from "@mui/icons-material/SensorDoorRounded";
import NoMeetingRoomIcon from "@mui/icons-material/NoMeetingRoomRounded";
import BlockIcon from "@mui/icons-material/BlockRounded";
import GlassCard from "@/components/GlassCard";
import { useAppTheme } from "@/context/ThemeContext";
import { fetchReportSummary, type ReportSummary } from "@/api/reports";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

type ReportFilters = {
    start_date: string;
    end_date: string;
    search: string;
};

export default function ReportsPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();

    const [filters, setFilters] = useState<ReportFilters>({
        start_date: "",
        end_date: "",
        search: "",
    });
    const [appliedFilters, setAppliedFilters] = useState<ReportFilters>({
        start_date: "",
        end_date: "",
        search: "",
    });
    const [data, setData] = useState<ReportSummary | null>(null);
    const [loading, setLoading] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const fromIso = appliedFilters.start_date
                ? new Date(`${appliedFilters.start_date}T00:00:00`).toISOString()
                : undefined;
            const toIso = appliedFilters.end_date
                ? new Date(`${appliedFilters.end_date}T23:59:59.999`).toISOString()
                : undefined;
            const res = await fetchReportSummary(fromIso, toIso);
            setData(res);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, [appliedFilters.start_date, appliedFilters.end_date]);

    const summaryData = [
        { key: "turnstile_in", label: "turnstileIn", icon: <LoginIcon sx={{ color: tokens.status.ok }} /> },
        { key: "turnstile_out", label: "turnstileOut", icon: <LogoutIcon sx={{ color: tokens.text.muted }} /> },
        { key: "esmo_ok", label: "esmoOk", icon: <MedicalServicesIcon sx={{ color: tokens.brand.secondary }} /> },
        { key: "esmo_fail", label: "esmoFail", icon: <ReportProblemIcon sx={{ color: tokens.status.error }} /> },
        { key: "tool_takes", label: "toolTakes", icon: <BuildIcon sx={{ color: tokens.status.warning }} /> },
        { key: "tool_returns", label: "toolReturns", icon: <HandymanIcon sx={{ color: tokens.status.ok }} /> },
        { key: "mine_in", label: "mineIn", icon: <SensorDoorIcon sx={{ color: "#8b5cf6" }} /> },
        { key: "mine_out", label: "mineOut", icon: <NoMeetingRoomIcon sx={{ color: tokens.text.muted }} /> },
        { key: "blocked", label: "blocked", icon: <BlockIcon sx={{ color: tokens.status.blocked }} /> },
    ] as const;

    const getMetricLabel = (row: (typeof summaryData)[number]) => {
        if (row.key === "esmo_fail") return "ESMO REVIEW";
        return t(`reports.metrics.${row.label}`);
    };

    const filteredSummaryData = useMemo(() => {
        const terms = appliedFilters.search.trim().toLowerCase().split(/\s+/).filter(Boolean);
        if (terms.length === 0) return summaryData;
        return summaryData.filter((row) => {
            const metricName = getMetricLabel(row).toLowerCase();
            return terms.every((term) => metricName.includes(term));
        });
    }, [appliedFilters.search, t]);

    const [leftSummaryData, rightSummaryData] = useMemo(() => {
        const middle = Math.ceil(filteredSummaryData.length / 2);
        return [filteredSummaryData.slice(0, middle), filteredSummaryData.slice(middle)];
    }, [filteredSummaryData]);

    const handleApply = () => {
        setAppliedFilters({
            start_date: filters.start_date,
            end_date: filters.end_date,
            search: filters.search.trim(),
        });
    };

    const exportCSV = () => {
        if (!data || filteredSummaryData.length === 0) return;
        let csv = `${t("reports.metric")},${t("reports.count")}\n`;
        filteredSummaryData.forEach((row) => {
            const val = data[row.key as keyof ReportSummary];
            csv += `${getMetricLabel(row)},${val}\n`;
        });
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `reports_${new Date().toISOString().split("T")[0]}.csv`);
        link.click();
    };

    const exportPDF = () => {
        if (!data || filteredSummaryData.length === 0) return;
        const doc = new jsPDF();

        doc.setFontSize(18);
        doc.text(t("reports.title"), 14, 22);

        doc.setFontSize(11);
        doc.setTextColor(100);
        doc.text(`${t("esmo.dateFrom")}: ${appliedFilters.start_date || "-"}`, 14, 30);
        doc.text(`${t("esmo.dateTo")}: ${appliedFilters.end_date || "-"}`, 14, 36);
        doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 42);

        const tableData = filteredSummaryData.map((row) => [
            getMetricLabel(row),
            data[row.key as keyof ReportSummary],
        ]);

        autoTable(doc, {
            head: [[t("reports.metric"), t("reports.count")]],
            body: tableData,
            startY: 50,
            theme: "grid",
            headStyles: { fillColor: [59, 130, 246] },
        });

        doc.save(`reports_${new Date().toISOString().split("T")[0]}.pdf`);
    };

    return (
        <Box>
            <Typography
                variant="h4"
                sx={{
                    mb: 3,
                    fontSize: "2.5rem",
                    fontWeight: 700,
                    background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    display: "inline-block",
                }}
            >
                {t("reports.title")}
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
                    disabled={!data || loading || filteredSummaryData.length === 0}
                    sx={{ height: 40, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap", background: "linear-gradient(135deg, #06b6d4, #3b82f6)", "&:hover": { background: "linear-gradient(135deg, #0891b2, #2563eb)" } }}
                >
                    {t("reports.exportCsv")}
                </Button>
                <Button
                    variant="contained"
                    startIcon={<PictureAsPdfIcon />}
                    onClick={exportPDF}
                    disabled={!data || loading || filteredSummaryData.length === 0}
                    sx={{ height: 40, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap", background: "linear-gradient(135deg, #06b6d4, #3b82f6)", "&:hover": { background: "linear-gradient(135deg, #0891b2, #2563eb)" } }}
                >
                    {t("reports.exportPdf")}
                </Button>
            </Box>

            <GlassCard sx={{ p: 0, overflow: "hidden" }}>
                <Typography variant="h6" sx={{ px: 3, pt: 3, pb: 2, fontWeight: 700, fontSize: "1.9rem", color: tokens.brand.primary }}>
                    {t("reports.dailySummary")}
                </Typography>
                <Box
                    sx={{
                        display: "grid",
                        gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                        gap: 0,
                        alignItems: "start",
                        borderTop: tokens.mode === "dark" ? "1px solid rgba(255,255,255,0.06)" : "1px solid rgba(0,0,0,0.06)",
                    }}
                >
                    <TableContainer
                        sx={{
                            overflowX: "hidden",
                        }}
                    >
                        <Table sx={{ tableLayout: "fixed" }}>
                            <TableHead>
                                <TableRow>
                                    <TableCell sx={{ width: "78%", fontWeight: 600, color: tokens.text.muted, bgcolor: tokens.bg.tableHeader }}>{t("reports.metric")}</TableCell>
                                    <TableCell align="center" sx={{ width: "22%", fontWeight: 600, color: tokens.text.muted, bgcolor: tokens.bg.tableHeader }}>
                                        {t("reports.count")}
                                    </TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {leftSummaryData.map((row) => (
                                    <TableRow
                                        key={`left-${row.key}`}
                                        sx={{
                                            "&:last-child td, &:last-child th": { border: 0 },
                                            "&:nth-of-type(even) td, &:nth-of-type(even) th": { bgcolor: tokens.bg.tableRowAlt },
                                        }}
                                    >
                                        <TableCell component="th" scope="row" sx={{ borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" }}>
                                            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                                                <Box
                                                    sx={{
                                                        p: 1,
                                                        borderRadius: "12px",
                                                        bgcolor: tokens.mode === "dark" ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)",
                                                        display: "flex",
                                                    }}
                                                >
                                                    {row.icon}
                                                </Box>
                                                <Typography variant="body1" fontWeight={500}>
                                                    {getMetricLabel(row)}
                                                </Typography>
                                            </Box>
                                        </TableCell>
                                        <TableCell align="center" sx={{ borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" }}>
                                            <Typography variant="h6" fontWeight={700} sx={{ color: data ? tokens.text.main : tokens.text.muted }}>
                                                {data ? data[row.key as keyof ReportSummary].toLocaleString() : "-"}
                                            </Typography>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>

                    <TableContainer
                        sx={{
                            overflowX: "hidden",
                            borderLeft: { md: tokens.mode === "dark" ? "1px solid rgba(255,255,255,0.06)" : "1px solid rgba(0,0,0,0.06)" },
                            borderTop: { xs: tokens.mode === "dark" ? "1px solid rgba(255,255,255,0.06)" : "1px solid rgba(0,0,0,0.06)", md: "none" },
                        }}
                    >
                        <Table sx={{ tableLayout: "fixed" }}>
                            <TableHead>
                                <TableRow>
                                    <TableCell sx={{ width: "78%", fontWeight: 600, color: tokens.text.muted, bgcolor: tokens.bg.tableHeader }}>{t("reports.metric")}</TableCell>
                                    <TableCell align="center" sx={{ width: "22%", fontWeight: 600, color: tokens.text.muted, bgcolor: tokens.bg.tableHeader }}>
                                        {t("reports.count")}
                                    </TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {rightSummaryData.map((row) => (
                                    <TableRow
                                        key={`right-${row.key}`}
                                        sx={{
                                            "&:last-child td, &:last-child th": { border: 0 },
                                            "&:nth-of-type(even) td, &:nth-of-type(even) th": { bgcolor: tokens.bg.tableRowAlt },
                                        }}
                                    >
                                        <TableCell component="th" scope="row" sx={{ borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" }}>
                                            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                                                <Box
                                                    sx={{
                                                        p: 1,
                                                        borderRadius: "12px",
                                                        bgcolor: tokens.mode === "dark" ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)",
                                                        display: "flex",
                                                    }}
                                                >
                                                    {row.icon}
                                                </Box>
                                                <Typography variant="body1" fontWeight={500}>
                                                    {getMetricLabel(row)}
                                                </Typography>
                                            </Box>
                                        </TableCell>
                                        <TableCell align="center" sx={{ borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" }}>
                                            <Typography variant="h6" fontWeight={700} sx={{ color: data ? tokens.text.main : tokens.text.muted }}>
                                                {data ? data[row.key as keyof ReportSummary].toLocaleString() : "-"}
                                            </Typography>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Box>
            </GlassCard>
        </Box>
    );
}
