import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
    Box,
    Typography,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    CircularProgress,
    IconButton,
    InputAdornment,
} from "@mui/material";
import VisibilityRoundedIcon from "@mui/icons-material/VisibilityRounded";
import VisibilityOffRoundedIcon from "@mui/icons-material/VisibilityOffRounded";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { fetchDevices, toggleDevicePower, type Device } from "@/api/devices";
import { useAppTheme } from "@/context/ThemeContext";

const allowedEsmoHosts = new Set(["192.168.8.17", "192.168.8.18", "192.168.8.19", "192.168.8.20"]);
const prioritizedTurnstileHosts = new Set(["192.168.1.180", "192.168.1.181"]);
const turnstileNameByHost: Record<string, string> = {
    "192.168.1.181": "shaxta kirish",
    "192.168.1.180": "shaxta chiqish",
};
const esmoMetaByHost: Record<string, { model: string; serial: string }> = {
    "192.168.8.17": { model: "MT-02", serial: "SN020245001" },
    "192.168.8.18": { model: "MT-02", serial: "SN020245009" },
    "192.168.8.19": { model: "MT", serial: "SN020245002" },
    "192.168.8.20": { model: "MT-02", serial: "SN020245004" },
};

const pageTitleGradientSx = {
    backgroundImage: "linear-gradient(45deg, #3b82f6 0%, #06b6d4 100%)",
    WebkitBackgroundClip: "text !important",
    backgroundClip: "text",
    WebkitTextFillColor: "transparent !important",
    color: "transparent !important",
    display: "inline-block",
};

const sectionTitleSx = {
    mb: 1,
    fontSize: "2.2rem",
    fontWeight: 700,
};

export default function DevicesPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [devices, setDevices] = useState<Device[]>([]);
    const [dialogDevice, setDialogDevice] = useState<Device | null>(null);
    const [dialogTargetActive, setDialogTargetActive] = useState<boolean>(true);
    const [powerPassword, setPowerPassword] = useState("");
    const [powerSaving, setPowerSaving] = useState(false);
    const [showPowerPassword, setShowPowerPassword] = useState(false);
    const visibleDevices = devices.filter((d) => {
        if (d.device_code === "ADMIN_PC" || d.device_code === "ESMO_PORTAL") return false;
        if (d.device_type !== "ESMO") return true;
        return !!d.host && allowedEsmoHosts.has(d.host);
    });
    const turnstileDevices = visibleDevices
        .filter((d) => d.device_type !== "ESMO")
        .sort((a, b) => {
            const aPriority = a.host && prioritizedTurnstileHosts.has(a.host) ? 0 : 1;
            const bPriority = b.host && prioritizedTurnstileHosts.has(b.host) ? 0 : 1;
            if (aPriority !== bPriority) return aPriority - bPriority;
            return 0;
        });
    const esmoDevices = visibleDevices.filter((d) => d.device_type === "ESMO");

    const load = async () => {
        try {
            const deviceRows = await fetchDevices();
            const normalized = deviceRows.map((d) => {
                const host = d.host || "";
                const forcedName = turnstileNameByHost[host];
                if (forcedName && d.device_type !== "ESMO" && d.name !== forcedName) {
                    return { ...d, name: forcedName };
                }
                return d;
            });
            setDevices(normalized);
        } catch {
            // Keep previous values if fetch fails.
        }
    };
    useEffect(() => {
        void load();
        const timer = window.setInterval(() => { void load(); }, 30000);
        return () => window.clearInterval(timer);
    }, []);

    const isDeviceOnline = (d: Device) => {
        return !!d.is_active;
    };

    const openPowerDialog = (device: Device, nextActive: boolean) => {
        setDialogDevice(device);
        setDialogTargetActive(nextActive);
        setPowerPassword("");
    };

    const closePowerDialog = () => {
        if (powerSaving) return;
        setDialogDevice(null);
        setPowerPassword("");
        setShowPowerPassword(false);
    };

    const savePowerState = async () => {
        if (!dialogDevice) return;
        setPowerSaving(true);
        try {
            await toggleDevicePower(dialogDevice.id, dialogTargetActive, powerPassword);
            await load();
            closePowerDialog();
        } catch (err) {
            const rawMessage = err instanceof Error ? err.message : "";
            const normalized = rawMessage.toLowerCase();
            if (normalized.includes("invalid control password")) {
                window.alert(t("devices.invalidPassword"));
            } else {
                window.alert(rawMessage || t("devices.powerUpdateError"));
            }
        } finally {
            setPowerSaving(false);
        }
    };

    const dataGridSx = {
        border: "none",
        "& .MuiDataGrid-columnHeaders": { bgcolor: tokens.bg.tableHeader },
        "& .MuiDataGrid-row:nth-of-type(even)": { bgcolor: tokens.bg.tableRowAlt },
        "& .MuiDataGrid-cell": { borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" },
        "& .MuiDataGrid-columnHeaderTitle": { fontWeight: 600 },
    };

    const turnstileColumns: GridColDef<Device>[] = [
        {
            field: "name",
            headerName: t("devices.col.name"),
            flex: 1,
            minWidth: 130,
            sortable: false,
        },
        {
            field: "host",
            headerName: t("devices.col.host"),
            flex: 1,
            minWidth: 145,
            sortable: false,
            renderCell: (params) => <Box sx={{ fontFamily: "monospace" }}>{params.row.host || "-"}</Box>,
        },
        {
            field: "device_type",
            headerName: t("devices.col.type"),
            width: 110,
            sortable: false,
        },
        {
            field: "status",
            headerName: t("devices.col.status"),
            width: 110,
            sortable: false,
            renderCell: (params) => <StatusPill status={isDeviceOnline(params.row) ? "ONLINE" : "OFFLINE"} />,
        },
        {
            field: "power_action",
            headerName: t("devices.col.power"),
            width: 130,
            sortable: false,
            filterable: false,
            renderCell: (params) => {
                const active = isDeviceOnline(params.row);
                return (
                    <Button
                        size="small"
                        variant="outlined"
                        color={active ? "error" : "primary"}
                        sx={{ textTransform: "none", borderRadius: "999px", fontWeight: 700 }}
                        onClick={() => openPowerDialog(params.row, !active)}
                    >
                        {active ? t("devices.turnOff") : t("devices.turnOn")}
                    </Button>
                );
            },
        },
    ];

    const esmoColumns: GridColDef<Device>[] = [
        {
            field: "name",
            headerName: t("devices.col.name"),
            flex: 1,
            minWidth: 120,
            sortable: false,
        },
        {
            field: "host",
            headerName: t("devices.col.host"),
            width: 120,
            sortable: false,
            renderCell: (params) => <Box sx={{ fontFamily: "monospace" }}>{params.row.host || "-"}</Box>,
        },
        {
            field: "serial",
            headerName: "Serial",
            width: 120,
            sortable: false,
            valueGetter: (_value, row) => (row.host ? esmoMetaByHost[row.host]?.serial || "-" : "-"),
            renderCell: (params) => <Box sx={{ fontFamily: "monospace" }}>{String(params.value || "-")}</Box>,
        },
        {
            field: "api_key",
            headerName: "API Key",
            flex: 1,
            minWidth: 180,
            sortable: false,
            renderCell: (params) => (
                <Box sx={{ fontFamily: "monospace", fontSize: 12, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {params.row.api_key || "-"}
                </Box>
            ),
        },
        {
            field: "status",
            headerName: t("devices.col.status"),
            width: 110,
            sortable: false,
            renderCell: (params) => <StatusPill status={isDeviceOnline(params.row) ? "ONLINE" : "OFFLINE"} />,
        },
        {
            field: "power_action",
            headerName: t("devices.col.power"),
            width: 120,
            sortable: false,
            filterable: false,
            renderCell: (params) => {
                const active = isDeviceOnline(params.row);
                return (
                    <Button
                        size="small"
                        variant="outlined"
                        color={active ? "error" : "primary"}
                        sx={{ textTransform: "none", borderRadius: "999px", fontWeight: 700 }}
                        onClick={() => openPowerDialog(params.row, !active)}
                    >
                        {active ? t("devices.turnOff") : t("devices.turnOn")}
                    </Button>
                );
            },
        },
    ];

    return (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <Typography variant="h4" sx={{
                fontSize: "2.5rem",
                fontWeight: 700,
                mb: 3
            }}>
                <Box component="span" sx={pageTitleGradientSx}>{t("devices.title")}</Box>
            </Typography>

            <Box
                sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
                    gap: 3,
                    width: "100%",
                    alignItems: "start",
                }}
            >
                <Box sx={{ minWidth: 0 }}>
                    <Typography variant="h5" sx={{ ...sectionTitleSx, color: tokens.brand.primary }}>Turniket</Typography>
                    <GlassCard sx={{ p: 0, width: "100%", overflowX: "hidden", "& .MuiDataGrid-root": { border: "none" } }}>
                        <DataGrid
                            autoHeight
                            rows={turnstileDevices}
                            columns={turnstileColumns}
                            disableColumnMenu
                            disableColumnSelector
                            disableRowSelectionOnClick
                            hideFooterSelectedRowCount
                            pageSizeOptions={[10, 25]}
                            initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
                            localeText={{ noRowsLabel: t("devices.noDevices") }}
                            sx={{ ...dataGridSx, width: "100%" }}
                        />
                    </GlassCard>
                </Box>

                <Box sx={{ minWidth: 0 }}>
                    <Typography variant="h5" sx={{ ...sectionTitleSx, color: tokens.brand.primary }}>Esmo</Typography>
                    <GlassCard sx={{ p: 0, width: "100%", overflowX: "hidden", "& .MuiDataGrid-root": { border: "none" } }}>
                        <DataGrid
                            autoHeight
                            rows={esmoDevices}
                            columns={esmoColumns}
                            disableColumnMenu
                            disableColumnSelector
                            disableRowSelectionOnClick
                            hideFooterSelectedRowCount
                            pageSizeOptions={[10, 25]}
                            initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
                            localeText={{ noRowsLabel: t("devices.noDevices") }}
                            sx={{ ...dataGridSx, width: "100%" }}
                        />
                    </GlassCard>
                </Box>
            </Box>

            <Dialog open={!!dialogDevice} onClose={closePowerDialog} fullWidth maxWidth="xs">
                <DialogTitle>{t("devices.powerDialogTitle")}</DialogTitle>
                <DialogContent sx={{ pt: 1 }}>
                    <Typography sx={{ mb: 2, color: tokens.text.secondary }}>
                        {dialogDevice
                            ? `${dialogDevice.name}: ${dialogTargetActive ? t("devices.turnOn") : t("devices.turnOff")}`
                            : ""}
                    </Typography>
                    <TextField
                        autoFocus
                        fullWidth
                        type={showPowerPassword ? "text" : "password"}
                        label={t("devices.password")}
                        value={powerPassword}
                        onChange={(e) => setPowerPassword(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !powerSaving) void savePowerState();
                        }}
                        InputProps={{
                            endAdornment: (
                                <InputAdornment position="end">
                                    <IconButton
                                        edge="end"
                                        onClick={() => setShowPowerPassword((v) => !v)}
                                        aria-label={showPowerPassword ? "hide password" : "show password"}
                                    >
                                        {showPowerPassword ? <VisibilityOffRoundedIcon /> : <VisibilityRoundedIcon />}
                                    </IconButton>
                                </InputAdornment>
                            ),
                        }}
                    />
                </DialogContent>
                <DialogActions sx={{ px: 3, pb: 2 }}>
                    <Button onClick={closePowerDialog} disabled={powerSaving} sx={{ textTransform: "none" }}>
                        {t("common.cancel", "Cancel")}
                    </Button>
                    <Button
                        variant="contained"
                        onClick={savePowerState}
                        disabled={powerSaving || !powerPassword}
                        sx={{ textTransform: "none" }}
                    >
                        {powerSaving ? <CircularProgress size={18} color="inherit" /> : t("common.confirm", "Confirm")}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
