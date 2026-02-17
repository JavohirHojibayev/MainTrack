import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, Grid, Button, Table, TableBody, TableCell, TableHead, TableRow, Select, MenuItem, FormControl, InputLabel, CircularProgress, Paper, Divider } from "@mui/material";
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

export default function ReportsPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [period, setPeriod] = useState("today");
    const [data, setData] = useState<ReportSummary | null>(null);
    const [loading, setLoading] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const now = new Date();
            let from = new Date();
            from.setHours(0, 0, 0, 0);
            let to = new Date();
            to.setHours(23, 59, 59, 999);

            if (period === "yesterday") {
                from.setDate(now.getDate() - 1);
                to.setDate(now.getDate() - 1);
            } else if (period === "week") {
                const day = now.getDay() || 7;
                from.setDate(now.getDate() - day + 1);
            } else if (period === "month") {
                from.setDate(1);
            }

            const res = await fetchReportSummary(from.toISOString(), to.toISOString());
            setData(res);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, [period]);

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
    ];

    const exportCSV = () => {
        if (!data) return;
        let csv = `${t("reports.metric")},${t("reports.count")}\n`;
        summaryData.forEach(row => {
            const val = data[row.key as keyof ReportSummary];
            csv += `${t(`reports.metrics.${row.label}`)},${val}\n`;
        });
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `report_${period}_${new Date().toISOString().split('T')[0]}.csv`);
        link.click();
    };

    const exportPDF = () => {
        if (!data) return;
        const doc = new jsPDF();

        doc.setFontSize(18);
        doc.text(t("reports.title"), 14, 22);

        doc.setFontSize(11);
        doc.setTextColor(100);
        doc.text(`Period: ${t(`reports.${period}`)}`, 14, 30);
        doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 36);

        const tableData = summaryData.map(row => [
            t(`reports.metrics.${row.label}`),
            data[row.key as keyof ReportSummary]
        ]);

        autoTable(doc, {
            head: [[t("reports.metric"), t("reports.count")]],
            body: tableData,
            startY: 44,
            theme: 'grid',
            headStyles: { fillColor: [59, 130, 246] },
        });

        doc.save(`report_${period}_${new Date().toISOString().split('T')[0]}.pdf`);
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
                }}>{t("reports.title")}</Typography>
            </Box>
            <GlassCard sx={{ mb: 3 }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} sm={4} md={3}>
                        <FormControl fullWidth size="small">
                            <InputLabel>{t("reports.period")}</InputLabel>
                            <Select value={period} label={t("reports.period")} onChange={(e) => setPeriod(e.target.value)}>
                                <MenuItem value="today">{t("reports.today")}</MenuItem>
                                <MenuItem value="yesterday">{t("reports.yesterday")}</MenuItem>
                                <MenuItem value="week">{t("reports.thisWeek")}</MenuItem>
                                <MenuItem value="month">{t("reports.thisMonth")}</MenuItem>
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item>
                        <Button
                            variant="contained"
                            startIcon={<DownloadIcon />}
                            onClick={exportCSV}
                            disabled={!data || loading}
                            sx={{ bgcolor: "#22c55e", "&:hover": { bgcolor: "#16a34a" } }}
                        >
                            {t("reports.exportCsv")}
                        </Button>
                    </Grid>
                    <Grid item>
                        <Button
                            variant="contained"
                            startIcon={<PictureAsPdfIcon />}
                            onClick={exportPDF}
                            disabled={!data || loading}
                            sx={{ bgcolor: "#ef4444", "&:hover": { bgcolor: "#dc2626" } }}
                        >
                            {t("reports.exportPdf")}
                        </Button>
                    </Grid>
                    {loading && <Grid item><CircularProgress size={24} /></Grid>}
                </Grid>
            </GlassCard>
            <GlassCard>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>{t("reports.dailySummary")}</Typography>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell sx={{ fontWeight: 600, color: tokens.text.muted }}>{t("reports.metric")}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600, color: tokens.text.muted }}>{t("reports.count")}</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {summaryData.map((row) => (
                            <TableRow key={row.key} sx={{ "&:last-child td, &:last-child th": { border: 0 } }}>
                                <TableCell component="th" scope="row">
                                    <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                                        <Box sx={{
                                            p: 1,
                                            borderRadius: "12px",
                                            bgcolor: tokens.mode === "dark" ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)",
                                            display: "flex"
                                        }}>
                                            {row.icon}
                                        </Box>
                                        <Typography variant="body1" fontWeight={500}>
                                            {t(`reports.metrics.${row.label}`)}
                                        </Typography>
                                    </Box>
                                </TableCell>
                                <TableCell align="right">
                                    <Typography variant="h6" fontWeight={700} sx={{ color: data ? tokens.text.main : tokens.text.muted }}>
                                        {data ? data[row.key as keyof ReportSummary].toLocaleString() : "—"}
                                    </Typography>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </GlassCard>
        </Box>
    );
}
