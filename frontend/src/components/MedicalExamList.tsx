import React, { useEffect, useState } from "react";
import {
    Box,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableRow,
    Chip,
    TableContainer,
    TablePagination
} from "@mui/material";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import GlassCard from "@/components/GlassCard";
import { fetchMedicalExams, type MedicalExam } from "@/api/medical";
import { useAppTheme } from "@/context/ThemeContext";

export const MedicalExamList: React.FC = () => {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [exams, setExams] = useState<MedicalExam[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(5);

    const loadExams = async () => {
        try {
            const data = await fetchMedicalExams({ limit: 50 });
            setExams(data);
        } catch (error) {
            console.error("Failed to load exams", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadExams();
        const interval = setInterval(loadExams, 30000);
        return () => clearInterval(interval);
    }, []);

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
                        <TableCell>Vitals</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {exams
                        .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                        .map((exam) => (
                            <TableRow key={exam.id} hover>
                                <TableCell sx={{ whiteSpace: "nowrap" }}>
                                    {dayjs(exam.timestamp).format("HH:mm:ss")}
                                </TableCell>
                                <TableCell>
                                    {exam.employee ? `${exam.employee.first_name} ${exam.employee.last_name}` : `ID: ${exam.employee_id}`}
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        label={exam.result}
                                        size="small"
                                        color={exam.result === "passed" ? "success" : "error"}
                                    />
                                </TableCell>
                                <TableCell sx={{ fontSize: "0.85rem" }}>
                                    {exam.pressure_systolic && `${exam.pressure_systolic}/${exam.pressure_diastolic}`}
                                    {exam.pulse && ` ❤️${exam.pulse}`}
                                    {exam.temperature && ` 🌡️${exam.temperature}°`}
                                </TableCell>
                            </TableRow>
                        ))}
                    {exams.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={4} sx={{ textAlign: "center", color: tokens.text.muted }}>
                                {t("dashboard.noData")}
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25]}
                component="div"
                count={exams.length}
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={(e, p) => setPage(p)}
                onRowsPerPageChange={(e) => {
                    setRowsPerPage(parseInt(e.target.value, 10));
                    setPage(0);
                }}
                sx={{ borderTop: "1px solid rgba(255,255,255,0.1)" }}
            />
        </GlassCard>
    );
};
