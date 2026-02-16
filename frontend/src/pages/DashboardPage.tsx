import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Grid, Typography, Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";
import PeopleIcon from "@mui/icons-material/PeopleRounded";
import MedicalIcon from "@mui/icons-material/MonitorHeartRounded";
import BuildIcon from "@mui/icons-material/BuildRounded";
import BlockIcon from "@mui/icons-material/BlockRounded";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { useAppTheme } from "@/context/ThemeContext";
import { fetchInsideMine, fetchToolDebts, fetchBlockedAttempts, type InsideMineRow, type ToolDebtRow, type BlockedRow } from "@/api/dashboard";

function KpiCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number; color: string }) {
    const { tokens } = useAppTheme();
    return (
        <GlassCard sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Box sx={{ width: 52, height: 52, borderRadius: `${tokens.radius.sm}px`, display: "flex", alignItems: "center", justifyContent: "center", bgcolor: `${color}22`, color }}>{icon}</Box>
            <Box>
                <Typography variant="h5" sx={{ fontWeight: 700, color }}>{value}</Typography>
                <Typography variant="body2">{label}</Typography>
            </Box>
        </GlassCard>
    );
}

function fmt(iso: string) {
    try { return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }); } catch { return iso; }
}

export default function DashboardPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [inside, setInside] = useState<InsideMineRow[]>([]);
    const [debts, setDebts] = useState<ToolDebtRow[]>([]);
    const [blocked, setBlocked] = useState<BlockedRow[]>([]);

    useEffect(() => {
        fetchInsideMine().then(setInside).catch(() => { });
        fetchToolDebts().then(setDebts).catch(() => { });
        fetchBlockedAttempts().then(setBlocked).catch(() => { });
    }, []);

    return (
        <Box>
            <Typography variant="h4" sx={{ mb: 3 }}>{t("dashboard.title")}</Typography>
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}><KpiCard icon={<PeopleIcon />} label={t("dashboard.insideMine")} value={inside.length} color={tokens.status.ok} /></Grid>
                <Grid item xs={12} sm={6} md={3}><KpiCard icon={<MedicalIcon />} label={t("dashboard.esmoOkToday")} value={inside.length} color={tokens.brand.secondary} /></Grid>
                <Grid item xs={12} sm={6} md={3}><KpiCard icon={<BuildIcon />} label={t("dashboard.toolDebts")} value={debts.length} color={tokens.status.warning} /></Grid>
                <Grid item xs={12} sm={6} md={3}><KpiCard icon={<BlockIcon />} label={t("dashboard.blockedAttempts")} value={blocked.length} color={tokens.status.blocked} /></Grid>
            </Grid>
            <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                    <GlassCard>
                        <Typography variant="h6" sx={{ mb: 2 }}>{t("dashboard.insideMine")}</Typography>
                        <Table size="small">
                            <TableHead><TableRow><TableCell>{t("dashboard.employee")}</TableCell><TableCell>{t("dashboard.name")}</TableCell><TableCell>{t("dashboard.in")}</TableCell></TableRow></TableHead>
                            <TableBody>
                                {inside.map((r) => <TableRow key={r.employee_no}><TableCell>{r.employee_no}</TableCell><TableCell>{r.full_name}</TableCell><TableCell>{fmt(r.last_in)}</TableCell></TableRow>)}
                                {inside.length === 0 && <TableRow><TableCell colSpan={3} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("dashboard.noData")}</TableCell></TableRow>}
                            </TableBody>
                        </Table>
                    </GlassCard>
                </Grid>
                <Grid item xs={12} md={4}>
                    <GlassCard>
                        <Typography variant="h6" sx={{ mb: 2 }}>{t("dashboard.toolDebts")}</Typography>
                        <Table size="small">
                            <TableHead><TableRow><TableCell>{t("dashboard.employee")}</TableCell><TableCell>{t("dashboard.name")}</TableCell><TableCell>{t("dashboard.taken")}</TableCell></TableRow></TableHead>
                            <TableBody>
                                {debts.map((r) => <TableRow key={r.employee_no}><TableCell>{r.employee_no}</TableCell><TableCell>{r.full_name}</TableCell><TableCell>{fmt(r.last_take)}</TableCell></TableRow>)}
                                {debts.length === 0 && <TableRow><TableCell colSpan={3} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("dashboard.noDebts")}</TableCell></TableRow>}
                            </TableBody>
                        </Table>
                    </GlassCard>
                </Grid>
                <Grid item xs={12} md={4}>
                    <GlassCard>
                        <Typography variant="h6" sx={{ mb: 2 }}>{t("dashboard.blockedAttempts")}</Typography>
                        <Table size="small">
                            <TableHead><TableRow><TableCell>{t("dashboard.type")}</TableCell><TableCell>{t("dashboard.time")}</TableCell><TableCell>{t("dashboard.reason")}</TableCell></TableRow></TableHead>
                            <TableBody>
                                {blocked.map((r, i) => <TableRow key={i}><TableCell><StatusPill status={r.event_type} /></TableCell><TableCell>{fmt(r.event_ts)}</TableCell><TableCell sx={{ color: tokens.status.blocked }}>{r.reject_reason}</TableCell></TableRow>)}
                                {blocked.length === 0 && <TableRow><TableCell colSpan={3} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("dashboard.clear")}</TableCell></TableRow>}
                            </TableBody>
                        </Table>
                    </GlassCard>
                </Grid>
            </Grid>
        </Box>
    );
}
