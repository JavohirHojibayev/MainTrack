import React, { useEffect, useState } from "react";
import {
    Box,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableRow,
    TablePagination
} from "@mui/material";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { fetchMedicalExams, fetchMedicalStats, type MedicalExam } from "@/api/medical";
import { useAppTheme } from "@/context/ThemeContext";

export const MedicalExamList: React.FC = () => {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [exams, setExams] = useState<MedicalExam[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(5);
    const [totalCount, setTotalCount] = useState(0);

    const getTodayTashkent = () => {
        const parts = new Intl.DateTimeFormat("en-US", {
            timeZone: "Asia/Tashkent",
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
        }).formatToParts(new Date());
        const yyyy = parts.find((p) => p.type === "year")?.value ?? "1970";
        const mm = parts.find((p) => p.type === "month")?.value ?? "01";
        const dd = parts.find((p) => p.type === "day")?.value ?? "01";
        return `${yyyy}-${mm}-${dd}`;
    };

    const loadExams = async (nextPage = page, nextRowsPerPage = rowsPerPage) => {
        try {
            const today = getTodayTashkent();
            const [data, stats] = await Promise.all([
                fetchMedicalExams({
                    skip: nextPage * nextRowsPerPage,
                    limit: nextRowsPerPage,
                    start_date: today,
                    end_date: today,
                }),
                fetchMedicalStats(today),
            ]);
            setExams(data);
            setTotalCount(stats.total);
            const maxPage = Math.max(0, Math.ceil(stats.total / nextRowsPerPage) - 1);
            if (nextPage > maxPage) {
                setPage(maxPage);
            }
        } catch (error) {
            console.error("Failed to load exams", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        setLoading(true);
        loadExams(page, rowsPerPage);
        const interval = setInterval(() => loadExams(page, rowsPerPage), 30000);
        return () => clearInterval(interval);
    }, [page, rowsPerPage]);

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
        if (s === "review" || s === "manual_review" || s === "ko'rik" || s === "korik") return "WARNING";
        if (s === "failed" || s === "fail" || s === "rejected") return "REJECTED";
        return "WARNING";
    };

    if (loading && exams.length === 0) {
        return <Typography sx={{ p: 2 }}>Loading exams...</Typography>;
    }

    return (
        <GlassCard>
            <Box sx={{ mb: 2, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <Typography variant="h6" sx={{ color: tokens.brand.secondary, fontWeight: 700 }}>
                    ESMO
                </Typography>
            </Box>
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell>{t("dashboard.time", "Time")}</TableCell>
                        <TableCell>{t("dashboard.employee", "Employee")}</TableCell>
                        <TableCell>{t("dashboard.status", "Result")}</TableCell>
                        <TableCell>BP</TableCell>
                        <TableCell>Pulse</TableCell>
                        <TableCell>Temp</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {exams
                        .map((exam) => {
                            const pressure =
                                exam.pressure_systolic == null || exam.pressure_diastolic == null
                                    ? "-"
                                    : `${exam.pressure_systolic}/${exam.pressure_diastolic}`;
                            const pulse = exam.pulse == null ? "-" : String(exam.pulse);
                            const temp = exam.temperature == null
                                ? "-"
                                : `${Number.isInteger(exam.temperature) ? exam.temperature.toFixed(0) : exam.temperature.toFixed(1)}\u00B0C`;

                            return (
                            <TableRow key={exam.id} hover>
                                <TableCell sx={{ whiteSpace: "nowrap" }}>
                                    {dayjs(exam.timestamp).format("HH:mm")}
                                </TableCell>
                                <TableCell>
                                    {exam.employee ? `${exam.employee.first_name} ${exam.employee.last_name}` : `ID: ${exam.employee_id}`}
                                </TableCell>
                                <TableCell>
                                    <StatusPill
                                        status={toDisplayStatus(String(exam.result ?? ""))}
                                        colorStatus={toColorStatus(String(exam.result ?? ""))}
                                    />
                                </TableCell>
                                <TableCell sx={{ whiteSpace: "nowrap", fontWeight: 600 }}>{pressure}</TableCell>
                                <TableCell sx={{ whiteSpace: "nowrap", fontWeight: 600 }}>{pulse}</TableCell>
                                <TableCell sx={{ whiteSpace: "nowrap", fontWeight: 600 }}>{temp}</TableCell>
                            </TableRow>
                            );
                        })}
                    {exams.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={6} sx={{ textAlign: "center", color: tokens.text.muted }}>
                                {t("dashboard.noData")}
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25]}
                component="div"
                count={totalCount}
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={(_e, p) => setPage(p)}
                onRowsPerPageChange={(e) => {
                    setRowsPerPage(parseInt(e.target.value, 10));
                    setPage(0);
                }}
                sx={{ borderTop: "1px solid rgba(255,255,255,0.1)" }}
            />
        </GlassCard>
    );
};
