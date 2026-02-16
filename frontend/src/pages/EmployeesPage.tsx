import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, TextField, Button, Grid, Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { fetchEmployees, createEmployee, type Employee, type EmployeeCreate } from "@/api/employees";
import { useAppTheme } from "@/context/ThemeContext";

const emptyForm: EmployeeCreate = { employee_no: "", first_name: "", last_name: "", patronymic: "", department: "", position: "" };

export default function EmployeesPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [form, setForm] = useState<EmployeeCreate>(emptyForm);

    const load = () => { fetchEmployees().then(setEmployees).catch(() => { }); };
    useEffect(() => { load(); }, []);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        try { await createEmployee(form); setForm(emptyForm); load(); } catch (err) { console.error(err); }
    };

    return (
        <Box>
            <Typography variant="h4" sx={{ mb: 3 }}>{t("employees.title")}</Typography>
            <GlassCard sx={{ mb: 3 }}>
                <Typography variant="h6" sx={{ mb: 2 }}>{t("employees.addEmployee")}</Typography>
                <Box component="form" onSubmit={handleSubmit}>
                    <Grid container spacing={2}>
                        <Grid item xs={12} sm={6} md={2}><TextField label={t("employees.employeeNo")} required fullWidth value={form.employee_no} onChange={(e) => setForm((f) => ({ ...f, employee_no: e.target.value }))} /></Grid>
                        <Grid item xs={12} sm={6} md={2}><TextField label={t("employees.firstName")} required fullWidth value={form.first_name} onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))} /></Grid>
                        <Grid item xs={12} sm={6} md={2}><TextField label={t("employees.lastName")} required fullWidth value={form.last_name} onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))} /></Grid>
                        <Grid item xs={12} sm={6} md={2}><TextField label={t("employees.patronymic")} fullWidth value={form.patronymic ?? ""} onChange={(e) => setForm((f) => ({ ...f, patronymic: e.target.value || null }))} /></Grid>
                        <Grid item xs={12} sm={6} md={2}><TextField label={t("employees.department")} fullWidth value={form.department ?? ""} onChange={(e) => setForm((f) => ({ ...f, department: e.target.value || null }))} /></Grid>
                        <Grid item xs={12} sm={6} md={2}><Button type="submit" variant="contained" fullWidth sx={{ height: 40 }}>{t("employees.create")}</Button></Grid>
                    </Grid>
                </Box>
            </GlassCard>
            <GlassCard>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>{t("employees.col.employeeNo")}</TableCell><TableCell>{t("employees.col.lastName")}</TableCell><TableCell>{t("employees.col.firstName")}</TableCell>
                            <TableCell>{t("employees.col.patronymic")}</TableCell><TableCell>{t("employees.col.department")}</TableCell><TableCell>{t("employees.col.position")}</TableCell><TableCell>{t("employees.col.status")}</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {employees.map((e) => (
                            <TableRow key={e.id}>
                                <TableCell>{e.employee_no}</TableCell><TableCell>{e.last_name}</TableCell><TableCell>{e.first_name}</TableCell>
                                <TableCell>{e.patronymic ?? "—"}</TableCell><TableCell>{e.department ?? "—"}</TableCell><TableCell>{e.position ?? "—"}</TableCell>
                                <TableCell><StatusPill status={e.is_active ? "OK" : "OFFLINE"} /></TableCell>
                            </TableRow>
                        ))}
                        {employees.length === 0 && <TableRow><TableCell colSpan={7} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("employees.noEmployees")}</TableCell></TableRow>}
                    </TableBody>
                </Table>
            </GlassCard>
        </Box>
    );
}
