import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Grid, Typography, Table, TableBody, TableCell, TableHead, TableRow, TablePagination } from "@mui/material";
import PeopleIcon from "@mui/icons-material/PeopleRounded";
import MedicalIcon from "@mui/icons-material/MonitorHeartRounded";
import BuildIcon from "@mui/icons-material/BuildRounded";
import BlockIcon from "@mui/icons-material/BlockRounded";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { useAppTheme } from "@/context/ThemeContext";
import { fetchDailyMineSummary, fetchToolDebts, fetchBlockedAttempts, fetchEsmoSummary, type DailySummaryRow, type ToolDebtRow, type BlockedRow } from "@/api/dashboard";

function KpiCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number | string | React.ReactNode; color: string }) {
    const { tokens } = useAppTheme();
    const isComplex = React.isValidElement(value) || (typeof value === "object" && value !== null);

    return (
        <GlassCard sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Box sx={{ width: 52, height: 52, borderRadius: `${tokens.radius.sm}px`, display: "flex", alignItems: "center", justifyContent: "center", bgcolor: `${color}22`, color }}>{icon}</Box>
            <Box>
                <Typography variant="h5" sx={{ fontWeight: 700, color: isComplex ? undefined : color, fontSize: typeof value === "string" && value.length > 5 ? "1.2rem" : "1.5rem" }}>{value}</Typography>
                <Typography variant="body2">{label}</Typography>
            </Box>
        </GlassCard>
    );
}

function fmt(iso: string | null) {
    if (!iso) return "—";
    try { return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }); } catch { return iso; }
}

function dur(min: number) {
    const h = Math.floor(min / 60);
    const m = min % 60;
    return `${h}h ${m}m`;
}

export default function DashboardPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [summary, setSummary] = useState<DailySummaryRow[]>([]);
    const [debts, setDebts] = useState<ToolDebtRow[]>([]);
    const [blocked, setBlocked] = useState<BlockedRow[]>([]);
    const [esmoCount, setEsmoCount] = useState(0);
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(10);

    // Side tables pagination
    const [debtsPage, setDebtsPage] = useState(0);
    const [debtsRowsPerPage, setDebtsRowsPerPage] = useState(5);
    const [blockedPage, setBlockedPage] = useState(0);
    const [blockedRowsPerPage, setBlockedRowsPerPage] = useState(5);

    useEffect(() => {
        const load = () => {
            const d = new Date();
            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            const today = `${year}-${month}-${day}`;

            fetchDailyMineSummary(today)
                .then(data => {
                    // Sort by last_in DESC
                    const sorted = data.sort((a, b) => {
                        const ta = a.last_in ? new Date(a.last_in).getTime() : 0;
                        const tb = b.last_in ? new Date(b.last_in).getTime() : 0;
                        return tb - ta;
                    });
                    setSummary(sorted);
                })
                .catch(() => { });
            fetchToolDebts().then(setDebts).catch(() => { });
            fetchBlockedAttempts().then(setBlocked).catch(() => { });
            fetchEsmoSummary(today).then(setEsmoCount).catch(() => { });
        };
        load();
        const interval = setInterval(load, 30000);
        return () => clearInterval(interval);
    }, []);

    const insideCount = summary.filter(r => r.is_inside).length;
    const enteredCount = summary.length;
    const exitedCount = summary.filter(r => !r.is_inside).length;

    return (
        <Box>
            <Typography variant="h4" sx={{
                mb: 3,
                fontSize: "2.5rem",
                fontWeight: 700,
                background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                display: "inline-block" // Ensure gradient applies correctly
            }}>{t("dashboard.title")}</Typography>
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <KpiCard
                        icon={<PeopleIcon />}
                        label={`${t("dashboard.statusInside")} / ${t("dashboard.statusOutside")}`}
                        value={
                            <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                <Box component="span" sx={{ color: "#f59e0b !important" }}>{insideCount}</Box>
                                <Box component="span" sx={{ color: tokens.text.muted + " !important", fontSize: "1.2rem" }}>/</Box>
                                <Box component="span" sx={{ color: "#10b981 !important" }}>{exitedCount}</Box>
                            </Box>
                        }
                        color={tokens.status.ok}
                    />
                </Grid>
                <Grid item xs={12} sm={6} md={3}><KpiCard icon={<MedicalIcon />} label={t("dashboard.esmoOkToday")} value={esmoCount} color={tokens.brand.secondary} /></Grid>
                <Grid item xs={12} sm={6} md={3}><KpiCard icon={<BuildIcon />} label={t("dashboard.toolDebts")} value={debts.length} color={tokens.status.warning} /></Grid>
                <Grid item xs={12} sm={6} md={3}><KpiCard icon={<BlockIcon />} label={t("dashboard.blockedAttempts")} value={blocked.length} color={tokens.status.blocked} /></Grid>
            </Grid>
            <Grid container spacing={2}>
                <Grid item xs={12} md={8}>
                    <GlassCard>
                        <Typography variant="h6" sx={{ mb: 2, color: tokens.status.ok, fontWeight: 700 }}>{t("dashboard.dailyActivity")}</Typography>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>{t("dashboard.employee")}</TableCell>
                                    <TableCell>{t("dashboard.name")}</TableCell>
                                    <TableCell>{t("dashboard.status")}</TableCell>
                                    <TableCell>{t("dashboard.entered")}</TableCell>
                                    <TableCell>{t("dashboard.exited")}</TableCell>
                                    <TableCell>{t("dashboard.duration")}</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {summary
                                    .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                                    .map((r) => (
                                        <TableRow key={r.employee_no}>
                                            <TableCell>{r.employee_no}</TableCell>
                                            <TableCell>{r.full_name}</TableCell>
                                            <TableCell><StatusPill status={r.is_inside ? t("dashboard.statusInside") : t("dashboard.statusOutside")} colorStatus={r.is_inside ? "INSIDE" : "OUTSIDE"} /></TableCell>
                                            <TableCell>{fmt(r.last_in)}</TableCell>
                                            <TableCell>{fmt(r.last_out)}</TableCell>
                                            <TableCell>{dur(r.total_minutes)}</TableCell>
                                        </TableRow>
                                    ))}
                                {summary.length === 0 && <TableRow><TableCell colSpan={6} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("dashboard.noData")}</TableCell></TableRow>}
                            </TableBody>
                        </Table>
                        <TablePagination
                            rowsPerPageOptions={[10, 25, 50]}
                            component="div"
                            count={summary.length}
                            rowsPerPage={rowsPerPage}
                            page={page}
                            onPageChange={(e, newPage) => setPage(newPage)}
                            onRowsPerPageChange={(e) => {
                                setRowsPerPage(parseInt(e.target.value, 10));
                                setPage(0);
                            }}
                        />
                    </GlassCard>
                </Grid>
                <Grid item xs={12} md={4}>
                    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                        <GlassCard>
                            <Typography variant="h6" sx={{ mb: 2, color: tokens.status.warning, fontWeight: 700 }}>{t("dashboard.toolDebts")}</Typography>
                            <Table size="small">
                                <TableHead><TableRow><TableCell>{t("dashboard.employee")}</TableCell><TableCell>{t("dashboard.taken")}</TableCell></TableRow></TableHead>
                                <TableBody>
                                    {debts
                                        .slice(debtsPage * debtsRowsPerPage, debtsPage * debtsRowsPerPage + debtsRowsPerPage)
                                        .map((r) => <TableRow key={r.employee_no}><TableCell>{r.full_name}</TableCell><TableCell>{fmt(r.last_take)}</TableCell></TableRow>)}
                                    {debts.length === 0 && <TableRow><TableCell colSpan={2} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("dashboard.noDebts")}</TableCell></TableRow>}
                                </TableBody>
                            </Table>
                            <TablePagination
                                rowsPerPageOptions={[5, 10, 25]}
                                component="div"
                                count={debts.length}
                                rowsPerPage={debtsRowsPerPage}
                                page={debtsPage}
                                onPageChange={(e, p) => setDebtsPage(p)}
                                onRowsPerPageChange={(e) => {
                                    setDebtsRowsPerPage(parseInt(e.target.value, 10));
                                    setDebtsPage(0);
                                }}
                                sx={{ borderTop: "1px solid rgba(255,255,255,0.1)" }}
                            />
                        </GlassCard>
                        <GlassCard>
                            <Typography variant="h6" sx={{ mb: 2, color: tokens.status.blocked, fontWeight: 700 }}>{t("dashboard.blockedAttempts")}</Typography>
                            <Table size="small">
                                <TableHead><TableRow><TableCell>{t("dashboard.time")}</TableCell><TableCell>{t("dashboard.reason")}</TableCell></TableRow></TableHead>
                                <TableBody>
                                    {blocked
                                        .slice(blockedPage * blockedRowsPerPage, blockedPage * blockedRowsPerPage + blockedRowsPerPage)
                                        .map((r, i) => <TableRow key={i}><TableCell>{fmt(r.event_ts)}</TableCell><TableCell sx={{ color: tokens.status.blocked }}>{r.reject_reason}</TableCell></TableRow>)}
                                    {blocked.length === 0 && <TableRow><TableCell colSpan={2} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("dashboard.clear")}</TableCell></TableRow>}
                                </TableBody>
                            </Table>
                            <TablePagination
                                rowsPerPageOptions={[5, 10, 25]}
                                component="div"
                                count={blocked.length}
                                rowsPerPage={blockedRowsPerPage}
                                page={blockedPage}
                                onPageChange={(e, p) => setBlockedPage(p)}
                                onRowsPerPageChange={(e) => {
                                    setBlockedRowsPerPage(parseInt(e.target.value, 10));
                                    setBlockedPage(0);
                                }}
                                sx={{ borderTop: "1px solid rgba(255,255,255,0.1)" }}
                            />
                        </GlassCard>
                    </Box>
                </Grid>
            </Grid>
        </Box>
    );
}
