import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Grid, Typography, Table, TableBody, TableCell, TableHead, TableRow, TablePagination, TableContainer } from "@mui/material";
import PeopleIcon from "@mui/icons-material/PeopleRounded";
import MedicalIcon from "@mui/icons-material/MonitorHeartRounded";
import BuildIcon from "@mui/icons-material/BuildRounded";
import BlockIcon from "@mui/icons-material/BlockRounded";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { MedicalExamList } from "@/components/MedicalExamList";
import { useAppTheme } from "@/context/ThemeContext";
import { fetchDailyMineSummary, fetchToolDebts, fetchBlockedAttemptsCount, fetchEsmoSummary24h, type DailySummaryRow, type ToolDebtRow, type EsmoSummary24h } from "@/api/dashboard";

const dashboardGradient = "linear-gradient(45deg, #3b82f6, #06b6d4)";
const dashboardGradientTextSx = {
    background: dashboardGradient,
    WebkitBackgroundClip: "text",
    backgroundClip: "text",
    WebkitTextFillColor: "transparent",
    color: "transparent",
    display: "inline-block",
};

function KpiCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number | string | React.ReactNode; color: string }) {
    const { tokens } = useAppTheme();
    const isComplex = React.isValidElement(value) || (typeof value === "object" && value !== null);

    return (
        <GlassCard sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Box sx={{ width: 52, height: 52, borderRadius: `${tokens.radius.sm}px`, display: "flex", alignItems: "center", justifyContent: "center", bgcolor: `${color}22`, color }}>{icon}</Box>
            <Box>
                {isComplex ? (
                    <Box
                        sx={{
                            fontWeight: 700,
                            fontSize: "1.5rem",
                            lineHeight: 1.2,
                            display: "flex",
                            alignItems: "center",
                            gap: 1,
                        }}
                    >
                        {value}
                    </Box>
                ) : (
                    <Typography
                        variant="h5"
                        sx={{
                            fontWeight: 700,
                            color,
                            fontSize: typeof value === "string" && value.length > 5 ? "1.2rem" : "1.5rem",
                            WebkitTextFillColor: "unset",
                            background: "none",
                        }}
                    >
                        {value}
                    </Typography>
                )}
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

function getLastActivityMs(row: DailySummaryRow): number {
    const inTs = row.last_in ? new Date(row.last_in).getTime() : 0;
    const outTs = row.last_out ? new Date(row.last_out).getTime() : 0;
    return Math.max(inTs, outTs);
}

function getTodayTashkent(): string {
    const parts = new Intl.DateTimeFormat("en-US", {
        timeZone: "Asia/Tashkent",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    }).formatToParts(new Date());
    const year = parts.find((p) => p.type === "year")?.value ?? "1970";
    const month = parts.find((p) => p.type === "month")?.value ?? "01";
    const day = parts.find((p) => p.type === "day")?.value ?? "01";
    return `${year}-${month}-${day}`;
}

function toTashkentDay(iso: string | null): string | null {
    if (!iso) return null;
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    const parts = new Intl.DateTimeFormat("en-US", {
        timeZone: "Asia/Tashkent",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    }).formatToParts(d);
    const year = parts.find((p) => p.type === "year")?.value ?? "1970";
    const month = parts.find((p) => p.type === "month")?.value ?? "01";
    const day = parts.find((p) => p.type === "day")?.value ?? "01";
    return `${year}-${month}-${day}`;
}

export default function DashboardPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [summary, setSummary] = useState<DailySummaryRow[]>([]);
    const [debts, setDebts] = useState<ToolDebtRow[]>([]);
    const [blockedCount, setBlockedCount] = useState(0);
    const [esmoSummary, setEsmoSummary] = useState<EsmoSummary24h>({ passed: 0, failed: 0, review: 0, total: 0 });
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(10);

    // Side tables pagination
    const [debtsPage, setDebtsPage] = useState(0);
    const [debtsRowsPerPage, setDebtsRowsPerPage] = useState(5);

    useEffect(() => {
        const load = () => {
            const today = getTodayTashkent();

            fetchDailyMineSummary(today)
                .then(data => {
                    // Sort by last activity time (either entry or exit) DESC
                    const sorted = data.sort((a, b) => {
                        const ta = getLastActivityMs(a);
                        const tb = getLastActivityMs(b);
                        return tb - ta;
                    });
                    setSummary(sorted);
                })
                .catch(() => { });
            fetchToolDebts(today).then(setDebts).catch(() => { });
            fetchBlockedAttemptsCount(today).then(setBlockedCount).catch(() => { setBlockedCount(0); });
            fetchEsmoSummary24h(today).then(setEsmoSummary).catch(() => { });
        };
        load();
        const interval = setInterval(load, 30000);
        return () => clearInterval(interval);
    }, []);

    const todayTashkent = getTodayTashkent();
    const enteredCount = summary.filter((r) => {
        if (typeof r.entered_today === "boolean") return r.entered_today;
        return toTashkentDay(r.last_in) === todayTashkent;
    }).length;
    const exitedCount = summary.filter((r) => {
        if (typeof r.exited_today === "boolean") return r.exited_today;
        return toTashkentDay(r.last_out) === todayTashkent;
    }).length;

    return (
        <Box>
            <Typography variant="h4" sx={{
                mb: 3,
                fontSize: "2.5rem",
                fontWeight: 700,
                ...dashboardGradientTextSx,
            }}>{t("dashboard.title")}</Typography>
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <KpiCard
                        icon={<PeopleIcon />}
                        label={t("dashboard.factoryInsideOutside")}
                        value={
                            <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                <Box component="span" sx={{ ...dashboardGradientTextSx }}>{enteredCount}</Box>
                                <Box component="span" sx={{ color: tokens.text.muted + " !important", fontSize: "1.2rem" }}>/</Box>
                                <Box component="span" sx={{ ...dashboardGradientTextSx }}>{exitedCount}</Box>
                            </Box>
                        }
                        color={tokens.status.ok}
                    />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <KpiCard
                        icon={<MedicalIcon />}
                        label={t("dashboard.esmoOkToday")}
                        value={
                            <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                <Box component="span" sx={{ ...dashboardGradientTextSx }}>{esmoSummary.passed}</Box>
                                <Box component="span" sx={{ color: tokens.text.muted, fontSize: "1.2rem" }}>/</Box>
                                <Box component="span" sx={{ ...dashboardGradientTextSx }}>{esmoSummary.failed}</Box>
                                <Box component="span" sx={{ color: tokens.text.muted, fontSize: "1.2rem" }}>/</Box>
                                <Box component="span" sx={{ ...dashboardGradientTextSx }}>{esmoSummary.review}</Box>
                            </Box>
                        }
                        color={tokens.brand.secondary}
                    />
                </Grid>
                <Grid item xs={12} sm={6} md={3}><KpiCard icon={<BuildIcon />} label={t("dashboard.toolDebts")} value={debts.length} color={tokens.status.warning} /></Grid>
                <Grid item xs={12} sm={6} md={3}><KpiCard icon={<BlockIcon />} label={t("dashboard.blockedAttempts")} value={blockedCount} color={tokens.status.blocked} /></Grid>
            </Grid>
            <Grid container spacing={2}>
                <Grid item xs={12} md={8}>
                    <GlassCard>
                        <Box sx={{ mb: 2, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <Typography variant="h6" sx={{ color: tokens.status.ok, fontWeight: 700 }}>{t("dashboard.factoryActivity")}</Typography>
                        </Box>
                        <TableContainer sx={{ maxHeight: 400 }}>
                            <Table size="small" stickyHeader>
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
                                            <TableRow key={r.employee_no} hover>
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
                        </TableContainer>
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
                    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
                        {/* Medical Exams Widget */}
                        <MedicalExamList />

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
                    </Box>
                </Grid>
            </Grid>
        </Box>
    );
}
