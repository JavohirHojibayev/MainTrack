import React, { useEffect, useState } from "react";
import {
    Box,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableRow,
    Paper,
    Chip,
    TableContainer
} from "@mui/material";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import { fetchMedicalExams, type MedicalExam } from "@/api/medical";
import { useAppTheme } from "@/context/ThemeContext";

export const MedicalExamList: React.FC = () => {
    const { t } = useTranslation();
    const { mode } = useAppTheme();
    const [exams, setExams] = useState<MedicalExam[]>([]);
    const [loading, setLoading] = useState(true);

    const loadExams = async () => {
        try {
            const data = await fetchMedicalExams({ limit: 10 });
            setExams(data);
        } catch (error) {
            console.error("Failed to load exams", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadExams();
        // Refresh every 30 seconds
        const interval = setInterval(loadExams, 30000);
        return () => clearInterval(interval);
    }, []);

    if (loading && exams.length === 0) {
        return <Typography sx={{ p: 2 }}>Loading exams...</Typography>;
    }

    return (
        <Paper
            elevation={0}
            sx={{
                p: 2,
                borderRadius: 4,
                border: "1px solid",
                borderColor: "divider",
                bgcolor: "background.paper",
                height: "100%",
                overflow: "hidden"
            }}
        >
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                <Typography variant="h6" fontWeight="bold">
                    🩺 {t("dashboard.medicalExams", "Recent Medical Exams")}
                </Typography>
                <Chip label="Live" color="success" size="small" variant="outlined" />
            </Box>

            <TableContainer sx={{ maxHeight: 400 }}>
                <Table size="small" stickyHeader>
                    <TableHead>
                        <TableRow>
                            <TableCell>Time</TableCell>
                            <TableCell>Employee</TableCell>
                            <TableCell>Result</TableCell>
                            <TableCell>Vitals</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {exams.map((exam) => (
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
                                    {exam.pressure_systolic && `${exam.pressure_systolic}/${exam.pressure_diastolic} mmHg`}
                                    {exam.pulse && `, ❤️ ${exam.pulse}`}
                                    {exam.temperature && `, 🌡️ ${exam.temperature}°C`}
                                </TableCell>
                            </TableRow>
                        ))}
                        {exams.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={4} align="center">
                                    No recent exams found.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
        </Paper>
    );
};
