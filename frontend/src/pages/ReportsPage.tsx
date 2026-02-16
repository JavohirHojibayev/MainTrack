import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, Grid, Button, Table, TableBody, TableCell, TableHead, TableRow, Select, MenuItem, FormControl, InputLabel } from "@mui/material";
import DownloadIcon from "@mui/icons-material/DownloadRounded";
import GlassCard from "@/components/GlassCard";
import { useAppTheme } from "@/context/ThemeContext";

export default function ReportsPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [period, setPeriod] = useState("today");

    const summaryData = [
        { key: "turnstileIn" }, { key: "turnstileOut" }, { key: "esmoOk" }, { key: "esmoFail" },
        { key: "toolTakes" }, { key: "toolReturns" }, { key: "mineIn" }, { key: "mineOut" }, { key: "blocked" },
    ];

    return (
        <Box>
            <Typography variant="h4" sx={{ mb: 3 }}>{t("reports.title")}</Typography>
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
                    <Grid item><Button variant="outlined" startIcon={<DownloadIcon />}>{t("reports.exportCsv")}</Button></Grid>
                    <Grid item><Button variant="outlined" startIcon={<DownloadIcon />}>{t("reports.exportPdf")}</Button></Grid>
                </Grid>
            </GlassCard>
            <GlassCard>
                <Typography variant="h6" sx={{ mb: 2 }}>{t("reports.dailySummary")}</Typography>
                <Table size="small">
                    <TableHead><TableRow><TableCell>{t("reports.metric")}</TableCell><TableCell align="right">{t("reports.count")}</TableCell></TableRow></TableHead>
                    <TableBody>
                        {summaryData.map((row) => (
                            <TableRow key={row.key}><TableCell>{t(`reports.metrics.${row.key}`)}</TableCell><TableCell align="right" sx={{ color: tokens.text.muted }}>—</TableCell></TableRow>
                        ))}
                    </TableBody>
                </Table>
            </GlassCard>
        </Box>
    );
}
