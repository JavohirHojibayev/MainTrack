import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, TextField, Button, Grid, Table, TableBody, TableCell, TableHead, TableRow, MenuItem } from "@mui/material";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { fetchDevices, createDevice, type Device, type DeviceCreate } from "@/api/devices";
import { useAppTheme } from "@/context/ThemeContext";

const deviceTypes = ["HIKVISION", "ESMO", "TOOL_FACE", "MINE_FACE", "OTHER"];
const emptyForm: DeviceCreate = { name: "", device_code: "", host: "", device_type: "HIKVISION", location: "", api_key: "" };

export default function DevicesPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [devices, setDevices] = useState<Device[]>([]);
    const [form, setForm] = useState<DeviceCreate>(emptyForm);

    const load = () => { fetchDevices().then(setDevices).catch(() => { }); };
    useEffect(() => { load(); }, []);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        try { await createDevice(form); setForm(emptyForm); load(); } catch (err) { console.error(err); }
    };

    return (
        <Box>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
                <Typography variant="h4" sx={{
                    background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    display: "inline-block"
                }}>{t("devices.title")}</Typography>
                <Box component="form" onSubmit={handleSubmit}>
                    <Grid container spacing={2}>
                        <Grid item xs={12} sm={6} md={2}><TextField label={t("devices.name")} required fullWidth value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} /></Grid>
                        <Grid item xs={12} sm={6} md={2}><TextField label={t("devices.host")} required fullWidth placeholder="192.168.x.x" value={form.host ?? ""} onChange={(e) => setForm((f) => ({ ...f, host: e.target.value || null, device_code: f.device_code || (e.target.value ? `HIK_${e.target.value.replace(/\./g, '_')}` : "") }))} /></Grid>
                        <Grid item xs={12} sm={6} md={2}><TextField label={t("devices.code")} required fullWidth value={form.device_code} onChange={(e) => setForm((f) => ({ ...f, device_code: e.target.value }))} /></Grid>
                        <Grid item xs={12} sm={6} md={2}>
                            <TextField label={t("devices.type")} select required fullWidth value={form.device_type} onChange={(e) => setForm((f) => ({ ...f, device_type: e.target.value }))}>
                                {deviceTypes.map((v) => <MenuItem key={v} value={v}>{v}</MenuItem>)}
                            </TextField>
                        </Grid>
                        <Grid item xs={12} sm={6} md={2}><Button type="submit" variant="contained" fullWidth sx={{ height: 40 }}>{t("devices.create")}</Button></Grid>
                    </Grid>
                </Box>
            </Box>
            <GlassCard>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>{t("devices.col.name")}</TableCell><TableCell>{t("devices.col.code")}</TableCell><TableCell>{t("devices.col.type")}</TableCell>
                            <TableCell>{t("devices.col.location")}</TableCell><TableCell>{t("devices.col.status")}</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {devices.map((d) => {
                            // Check if online (last_seen within 10 minutes)
                            const isOnline = d.last_seen && (new Date().getTime() - new Date(d.last_seen).getTime() < 10 * 60 * 1000);
                            return (
                                <TableRow key={d.id}>
                                    <TableCell>{d.name}</TableCell>
                                    <TableCell sx={{ fontFamily: "monospace", fontWeight: 600 }}>{d.host || d.device_code}</TableCell>
                                    <TableCell>{d.device_type}</TableCell>
                                    <TableCell>{d.location ?? "—"}</TableCell>
                                    <TableCell><StatusPill status={isOnline ? "ONLINE" : "OFFLINE"} /></TableCell>
                                </TableRow>
                            );
                        })}
                        {devices.length === 0 && <TableRow><TableCell colSpan={5} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("devices.noDevices")}</TableCell></TableRow>}
                    </TableBody>
                </Table>
            </GlassCard>
        </Box>
    );
}
