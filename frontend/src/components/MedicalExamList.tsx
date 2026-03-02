import React, { useEffect, useMemo, useState } from "react";
import {
    Box,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableRow,
    TablePagination,
    TableContainer,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { fetchMedicalExams, type MedicalExam } from "@/api/medical";
import { useAppTheme } from "@/context/ThemeContext";

interface MedicalExamListProps {
    searchQuery?: string;
    day?: string;
    onStatsChange?: (stats: { passed: number; review: number; failed: number; total: number }) => void;
}

export const MedicalExamList: React.FC<MedicalExamListProps> = ({ searchQuery = "", day, onStatsChange }) => {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [exams, setExams] = useState<MedicalExam[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(5);

    const buildEmployeeName = (exam: MedicalExam): string => {
        if (exam.employee_full_name) return exam.employee_full_name;
        const emp = exam.employee;
        if (!emp) return `ID: ${exam.employee_id}`;
        const parts = [emp.last_name, emp.first_name, emp.patronymic].filter(Boolean);
        return parts.join(" ");
    };

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

    const getExamDay = (rawTimestamp: string): string | null => {
        const match = String(rawTimestamp || "").match(/^(\d{4}-\d{2}-\d{2})/);
        if (match) return match[1];

        const d = new Date(rawTimestamp);
        if (Number.isNaN(d.getTime())) return null;
        const parts = new Intl.DateTimeFormat("en-US", {
            timeZone: "Asia/Tashkent",
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
        }).formatToParts(d);
        const yyyy = parts.find((p) => p.type === "year")?.value ?? "1970";
        const mm = parts.find((p) => p.type === "month")?.value ?? "01";
        const dd = parts.find((p) => p.type === "day")?.value ?? "01";
        return `${yyyy}-${mm}-${dd}`;
    };

    const loadExams = async () => {
        try {
            const targetDay = day || getTodayTashkent();
            const data = await fetchMedicalExams({
                skip: 0,
                limit: 5000,
                start_date: targetDay,
                end_date: targetDay,
                latest_per_employee: true,
            });
            const dailyData = data.filter((exam) => getExamDay(exam.timestamp) === targetDay);
            setExams(dailyData);
            if (onStatsChange) {
                let passed = 0;
                let review = 0;
                let failed = 0;
                for (const exam of dailyData) {
                    const s = String(exam.result || "").toLowerCase();
                    if (s === "passed") passed += 1;
                    else if (s === "review" || s === "manual_review" || s === "ko'rik" || s === "korik") review += 1;
                    else if (s === "failed" || s === "fail" || s === "rejected") failed += 1;
                }
                onStatsChange({ passed, review, failed, total: dailyData.length });
            }
        } catch (error) {
            console.error("Failed to load exams", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        setPage(0);
    }, [searchQuery]);

    useEffect(() => {
        setLoading(true);
        loadExams();
        const interval = setInterval(() => loadExams(), 30000);
        return () => clearInterval(interval);
    }, [rowsPerPage, day]);

    const filteredExams = useMemo(() => {
        const terms = searchQuery.trim().toLowerCase().split(/\s+/).filter(Boolean);
        if (!terms.length) return exams;
        return exams.filter((exam) => {
            const fullName = buildEmployeeName(exam);
            const employeeNo = exam.employee?.employee_no || "";
            const haystack = `${fullName} ${employeeNo}`.toLowerCase();
            return terms.every((term) => haystack.includes(term));
        });
    }, [exams, searchQuery]);

    const pagedExams = useMemo(
        () => filteredExams.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage),
        [filteredExams, page, rowsPerPage]
    );

    useEffect(() => {
        const maxPage = Math.max(0, Math.ceil(filteredExams.length / rowsPerPage) - 1);
        if (page > maxPage) {
            setPage(maxPage);
        }
    }, [filteredExams.length, page, rowsPerPage]);

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
            <TableContainer sx={{ maxHeight: 300, overflowY: "auto", overflowX: "hidden" }}>
                <Table size="small" stickyHeader sx={{ width: "100%", tableLayout: "fixed" }}>
                    <TableHead>
                        <TableRow>
                            <TableCell sx={{ width: 56 }}>{t("dashboard.time", "Time")}</TableCell>
                            <TableCell>{t("dashboard.employee", "Employee")}</TableCell>
                            <TableCell sx={{ width: 112 }}>{t("dashboard.status", "Result")}</TableCell>
                            <TableCell sx={{ width: 64 }}>BP</TableCell>
                            <TableCell sx={{ width: 58 }}>Pulse</TableCell>
                            <TableCell sx={{ width: 68 }}>Temp</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {pagedExams
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
                                    <TableCell sx={{ whiteSpace: "nowrap", width: 56 }}>
                                        {dayjs(exam.timestamp).format("HH:mm")}
                                    </TableCell>
                                    <TableCell sx={{ overflowWrap: "anywhere" }}>
                                        {buildEmployeeName(exam)}
                                    </TableCell>
                                    <TableCell sx={{ width: 112 }}>
                                        <StatusPill
                                            status={toDisplayStatus(String(exam.result ?? ""))}
                                            colorStatus={toColorStatus(String(exam.result ?? ""))}
                                        />
                                    </TableCell>
                                    <TableCell sx={{ whiteSpace: "nowrap", width: 64 }}>{pressure}</TableCell>
                                    <TableCell sx={{ whiteSpace: "nowrap", width: 58 }}>{pulse}</TableCell>
                                    <TableCell sx={{ whiteSpace: "nowrap", width: 68 }}>{temp}</TableCell>
                                </TableRow>
                                );
                            })}
                        {pagedExams.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={6} sx={{ textAlign: "center", color: tokens.text.muted }}>
                                    {t("dashboard.noData")}
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25, 50]}
                component="div"
                count={filteredExams.length}
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
