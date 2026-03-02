import React, { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useOutletContext } from "react-router-dom";
import { Box, Grid, Typography, Table, TableBody, TableCell, TableHead, TableRow, TablePagination, TableContainer } from "@mui/material";
import PeopleIcon from "@mui/icons-material/PeopleRounded";
import MedicalIcon from "@mui/icons-material/MonitorHeartRounded";
import BuildIcon from "@mui/icons-material/BuildRounded";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { MedicalExamList } from "@/components/MedicalExamList";
import { useAppTheme } from "@/context/ThemeContext";
import { fetchDailyMineSummary, fetchToolDebts, type DailySummaryRow, type ToolDebtRow } from "@/api/dashboard";

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
        <GlassCard sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 2, py: 1.5 }}>
            <Box sx={{ width: 44, height: 44, borderRadius: `${tokens.radius.sm}px`, display: "flex", alignItems: "center", justifyContent: "center", bgcolor: `${color}22`, color }}>{icon}</Box>
            <Box>
                {isComplex ? (
                    <Box
                        sx={{
                            fontWeight: 700,
                            fontSize: "1.2rem",
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
                            fontSize: typeof value === "string" && value.length > 5 ? "1rem" : "1.2rem",
                            WebkitTextFillColor: "unset",
                            background: "none",
                        }}
                    >
                        {value}
                    </Typography>
                )}
                <Typography variant="body2" sx={{ fontSize: "0.82rem" }}>{label}</Typography>
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

export default function DashboardPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const { searchQuery } = useOutletContext<{ searchQuery: string }>();
    const [summary, setSummary] = useState<DailySummaryRow[]>([]);
    const [debts, setDebts] = useState<ToolDebtRow[]>([]);
    const [dashboardDay, setDashboardDay] = useState<string>(getTodayTashkent());
    const [esmoSummary, setEsmoSummary] = useState<{ passed: number; failed: number; review: number; total: number }>({ passed: 0, failed: 0, review: 0, total: 0 });
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(10);

    // Side tables pagination
    const [debtsPage, setDebtsPage] = useState(0);
    const [debtsRowsPerPage, setDebtsRowsPerPage] = useState(5);

    useEffect(() => {
        const load = () => {
            const today = getTodayTashkent();
            setDashboardDay(today);

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
        };
        load();
        const interval = setInterval(load, 30000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        setPage(0);
        setDebtsPage(0);
    }, [searchQuery]);

    const normalizedSearch = searchQuery.trim().toLowerCase();
    const dailySummary = summary;
    const dailyDebts = debts;

    const filteredSummary = useMemo(() => {
        const terms = normalizedSearch.split(/\s+/).filter(Boolean);
        if (terms.length === 0) return dailySummary;
        return dailySummary.filter((r) => {
            const haystack = `${r.full_name || ""} ${r.employee_no || ""}`.toLowerCase();
            return terms.every((term) => haystack.includes(term));
        });
    }, [dailySummary, normalizedSearch]);

    const filteredDebts = useMemo(() => {
        const terms = normalizedSearch.split(/\s+/).filter(Boolean);
        if (terms.length === 0) return dailyDebts;
        return dailyDebts.filter((r) => {
            const haystack = `${r.full_name || ""} ${r.employee_no || ""}`.toLowerCase();
            return terms.every((term) => haystack.includes(term));
        });
    }, [dailyDebts, normalizedSearch]);

    const insideCount = dailySummary.filter((r) => Boolean(r.entered_today)).length;
    const outsideCount = dailySummary.filter((r) => Boolean(r.exited_today)).length;

    return (
        <Box>
            <Typography variant="h4" sx={{
                mb: 3,
                fontSize: "2.5rem",
                fontWeight: 700,
                ...dashboardGradientTextSx,
            }}>{t("dashboard.title")}</Typography>
            <Grid container spacing={2}>
                <Grid item xs={12} md={7}>
                    <Box
                        sx={{
                            mb: 2,
                            display: "grid",
                            gap: 2,
                            gridTemplateColumns: {
                                xs: "1fr",
                                sm: "repeat(3, minmax(0, 1fr))",
                            },
                            alignItems: "stretch",
                            width: "100%",
                        }}
                    >
                        <KpiCard
                            icon={<PeopleIcon />}
                            label={t("dashboard.factoryInsideOutside")}
                            value={
                                <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                    <Box component="span" sx={{ ...dashboardGradientTextSx }}>{insideCount}</Box>
                                    <Box component="span" sx={{ color: tokens.text.muted + " !important", fontSize: "1.1rem" }}>/</Box>
                                    <Box component="span" sx={{ ...dashboardGradientTextSx }}>{outsideCount}</Box>
                                </Box>
                            }
                            color={tokens.status.ok}
                        />
                        <KpiCard
                            icon={<MedicalIcon />}
                            label={t("dashboard.esmoOkToday")}
                            value={
                                <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                    <Box component="span" sx={{ ...dashboardGradientTextSx }}>{esmoSummary.passed}</Box>
                                    <Box component="span" sx={{ color: tokens.text.muted, fontSize: "1.1rem" }}>/</Box>
                                    <Box component="span" sx={{ ...dashboardGradientTextSx }}>{esmoSummary.review}</Box>
                                    <Box component="span" sx={{ color: tokens.text.muted, fontSize: "1.1rem" }}>/</Box>
                                    <Box component="span" sx={{ ...dashboardGradientTextSx }}>{esmoSummary.failed}</Box>
                                </Box>
                            }
                            color={tokens.brand.secondary}
                        />
                        <KpiCard icon={<BuildIcon />} label={t("dashboard.toolDebts")} value={dailyDebts.length} color={tokens.status.warning} />
                    </Box>
                    <GlassCard>
                        <Box sx={{ mb: 2, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <Typography variant="h6" sx={{ color: tokens.status.ok, fontWeight: 700 }}>{t("dashboard.factoryActivity")}</Typography>
                        </Box>
                        <TableContainer sx={{ maxHeight: 400 }}>
                            <Table size="small" stickyHeader sx={{ width: "100%", tableLayout: "fixed" }}>
                                <TableHead>
                                    <TableRow>
                                        <TableCell sx={{ width: 130 }}>{t("dashboard.employee")}</TableCell>
                                        <TableCell sx={{ width: "36%" }}>{t("dashboard.name")}</TableCell>
                                        <TableCell sx={{ width: 120 }}>{t("dashboard.status")}</TableCell>
                                        <TableCell sx={{ width: 95 }}>{t("dashboard.entered")}</TableCell>
                                        <TableCell sx={{ width: 95 }}>{t("dashboard.exited")}</TableCell>
                                        <TableCell sx={{ width: 95 }}>{t("dashboard.duration")}</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {filteredSummary
                                        .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                                        .map((r) => (
                                            <TableRow key={r.employee_no} hover>
                                                <TableCell sx={{ width: 130 }}>{r.employee_no}</TableCell>
                                                <TableCell sx={{ width: "36%", maxWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                                    {r.full_name}
                                                </TableCell>
                                                <TableCell sx={{ width: 120 }}>
                                                    <StatusPill status={r.is_inside ? t("dashboard.statusInside") : t("dashboard.statusOutside")} colorStatus={r.is_inside ? "INSIDE" : "OUTSIDE"} />
                                                </TableCell>
                                                <TableCell sx={{ width: 95 }}>{fmt(r.last_in)}</TableCell>
                                                <TableCell sx={{ width: 95 }}>{fmt(r.last_out)}</TableCell>
                                                <TableCell sx={{ width: 95 }}>{dur(r.total_minutes)}</TableCell>
                                            </TableRow>
                                        ))}
                                    {filteredSummary.length === 0 && <TableRow><TableCell colSpan={6} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("dashboard.noData")}</TableCell></TableRow>}
                                </TableBody>
                            </Table>
                        </TableContainer>
                        <TablePagination
                            rowsPerPageOptions={[10, 25, 50]}
                            component="div"
                            count={filteredSummary.length}
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
                <Grid item xs={12} md={5}>
                    <Box sx={{ display: "flex", flexDirection: "column", gap: 3, width: "100%", "& > *": { width: "100%" } }}>
                        {/* Medical Exams Widget */}
                        <MedicalExamList
                            searchQuery={searchQuery}
                            day={dashboardDay}
                            onStatsChange={setEsmoSummary}
                        />

                        <GlassCard sx={{ width: "100%" }}>
                            <Typography variant="h6" sx={{ mb: 2, color: tokens.status.warning, fontWeight: 700 }}>{t("dashboard.toolDebts")}</Typography>
                            <TableContainer sx={{ maxHeight: 300, overflowY: "auto" }}>
                                <Table size="small" stickyHeader>
                                    <TableHead><TableRow><TableCell>{t("dashboard.employee")}</TableCell><TableCell>{t("dashboard.taken")}</TableCell></TableRow></TableHead>
                                    <TableBody>
                                        {filteredDebts
                                            .slice(debtsPage * debtsRowsPerPage, debtsPage * debtsRowsPerPage + debtsRowsPerPage)
                                            .map((r) => <TableRow key={r.employee_no}><TableCell>{r.full_name}</TableCell><TableCell>{fmt(r.last_take)}</TableCell></TableRow>)}
                                        {filteredDebts.length === 0 && <TableRow><TableCell colSpan={2} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("dashboard.noDebts")}</TableCell></TableRow>}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                            <TablePagination
                                rowsPerPageOptions={[5, 10, 25, 50]}
                                component="div"
                                count={filteredDebts.length}
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
