import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { fetchDevices, type Device } from "@/api/devices";
import { useAppTheme } from "@/context/ThemeContext";

const allowedEsmoHosts = new Set(["192.168.8.17", "192.168.8.18", "192.168.8.19", "192.168.8.20"]);
const esmoMetaByHost: Record<string, { model: string; serial: string }> = {
    "192.168.8.17": { model: "MT-02", serial: "SN020245001" },
    "192.168.8.18": { model: "MT-02", serial: "SN020245009" },
    "192.168.8.19": { model: "MT", serial: "SN020245002" },
    "192.168.8.20": { model: "MT-02", serial: "SN020245004" },
};

export default function DevicesPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [devices, setDevices] = useState<Device[]>([]);
    const visibleDevices = devices.filter((d) => {
        if (d.device_code === "ADMIN_PC" || d.device_code === "ESMO_PORTAL") return false;
        if (d.device_type !== "ESMO") return true;
        return !!d.host && allowedEsmoHosts.has(d.host);
    });
    const turnstileDevices = visibleDevices.filter((d) => d.device_type !== "ESMO");
    const esmoDevices = visibleDevices.filter((d) => d.device_type === "ESMO");

    const load = () => { fetchDevices().then(setDevices).catch(() => { }); };
    useEffect(() => { load(); }, []);
    const isDeviceOnline = (d: Device) => !!(d.last_seen && (new Date().getTime() - new Date(d.last_seen).getTime() < 10 * 60 * 1000));

    return (
        <Box>
            <Typography variant="h4" sx={{
                fontSize: "2.5rem",
                fontWeight: 700,
                background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                display: "inline-block",
                mb: 3
            }}>{t("devices.title")}</Typography>

            <Typography variant="h5" sx={{
                mt: 2,
                mb: 1.5,
                fontSize: "2rem",
                fontWeight: 700,
                background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                display: "block",
            }}>Turniket</Typography>
            <GlassCard sx={{ width: "fit-content", minWidth: 980, mb: 3 }}>
                <Table size="small" sx={{ width: "auto", minWidth: 980 }}>
                    <TableHead>
                        <TableRow>
                            <TableCell>{t("devices.col.name")}</TableCell>
                            <TableCell>{t("devices.col.host")}</TableCell>
                            <TableCell>{t("devices.col.code")}</TableCell>
                            <TableCell>{t("devices.col.type")}</TableCell>
                            <TableCell>{t("devices.col.location")}</TableCell>
                            <TableCell>{t("devices.col.status")}</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {turnstileDevices.map((d) => (
                            <TableRow key={d.id}>
                                <TableCell>{d.name}</TableCell>
                                <TableCell sx={{ fontFamily: "monospace" }}>{d.host || "-"}</TableCell>
                                <TableCell sx={{ fontFamily: "monospace" }}>{d.device_code}</TableCell>
                                <TableCell>{d.device_type}</TableCell>
                                <TableCell>{d.location === "MINE" ? t("devices.locationMine") : t("devices.locationFactory")}</TableCell>
                                <TableCell><StatusPill status={isDeviceOnline(d) ? "ONLINE" : "OFFLINE"} /></TableCell>
                            </TableRow>
                        ))}
                        {turnstileDevices.length === 0 && <TableRow><TableCell colSpan={6} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("devices.noDevices")}</TableCell></TableRow>}
                    </TableBody>
                </Table>
            </GlassCard>

            <Typography variant="h5" sx={{
                mb: 1.5,
                fontSize: "2rem",
                fontWeight: 700,
                background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                display: "block",
            }}>ESMO</Typography>
            <GlassCard sx={{ width: "fit-content", minWidth: 1200 }}>
                <Table size="small" sx={{ width: "auto", minWidth: 1200 }}>
                    <TableHead>
                        <TableRow>
                            <TableCell>{t("devices.col.name")}</TableCell>
                            <TableCell>{t("devices.col.host")}</TableCell>
                            <TableCell>{t("devices.col.code")}</TableCell>
                            <TableCell>Model</TableCell>
                            <TableCell>Serial</TableCell>
                            <TableCell>API Key</TableCell>
                            <TableCell>{t("devices.col.type")}</TableCell>
                            <TableCell>{t("devices.col.location")}</TableCell>
                            <TableCell>{t("devices.col.status")}</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {esmoDevices.map((d) => {
                            const esmoMeta = (d.host && esmoMetaByHost[d.host]) || null;
                            return (
                                <TableRow key={d.id}>
                                    <TableCell>{d.name}</TableCell>
                                    <TableCell sx={{ fontFamily: "monospace" }}>{d.host || "-"}</TableCell>
                                    <TableCell sx={{ fontFamily: "monospace" }}>{d.device_code}</TableCell>
                                    <TableCell>{esmoMeta?.model || "-"}</TableCell>
                                    <TableCell sx={{ fontFamily: "monospace" }}>{esmoMeta?.serial || "-"}</TableCell>
                                    <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{d.api_key || "-"}</TableCell>
                                    <TableCell>{d.device_type}</TableCell>
                                    <TableCell>{d.location === "MINE" ? t("devices.locationMine") : t("devices.locationFactory")}</TableCell>
                                    <TableCell><StatusPill status={isDeviceOnline(d) ? "ONLINE" : "OFFLINE"} /></TableCell>
                                </TableRow>
                            );
                        })}
                        {esmoDevices.length === 0 && <TableRow><TableCell colSpan={9} sx={{ textAlign: "center", color: tokens.text.muted }}>{t("devices.noDevices")}</TableCell></TableRow>}
                    </TableBody>
                </Table>
            </GlassCard>
        </Box>
    );
}
