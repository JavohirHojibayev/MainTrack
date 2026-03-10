import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, TextField, Button } from "@mui/material";
import { DataGrid, type GridColDef, type GridPaginationModel } from "@mui/x-data-grid";
import DownloadIcon from "@mui/icons-material/DownloadRounded";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdfRounded";
import GlassCard from "@/components/GlassCard";
import LocalizedDateInput from "@/components/LocalizedDateInput";
import StatusPill from "@/components/StatusPill";
import { useAppTheme } from "@/context/ThemeContext";
import { formatEmployeeNo } from "@/utils/employeeNo";
import { fetchEventsPaged, type EventFilters, type EventRow } from "@/api/events";

const pageTitleGradientSx = {
    backgroundImage: "linear-gradient(45deg, #3b82f6 0%, #06b6d4 100%)",
    WebkitBackgroundClip: "text !important",
    backgroundClip: "text",
    WebkitTextFillColor: "transparent !important",
    color: "transparent !important",
    display: "inline-block",
};

type MainJournalFilters = {
    date_from?: string;
    date_to?: string;
    search?: string;
};

export default function MainJournalPage() {
    const { t, i18n } = useTranslation();
    const { tokens } = useAppTheme();
    const [filters, setFilters] = useState<MainJournalFilters>({});
    const [appliedFilters, setAppliedFilters] = useState<MainJournalFilters>({});
    const [rows, setRows] = useState<EventRow[]>([]);
    const [loading, setLoading] = useState(false);
    const [rowCount, setRowCount] = useState(0);
    const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 25 });

    const lang = String(i18n.resolvedLanguage || i18n.language || "").toLowerCase();
    const mainJournalTitle = t("mainJournal.title", {
        defaultValue: lang.startsWith("ru")
            ? "\u0416\u0443\u0440\u043d\u0430\u043b \u0448\u0430\u0445\u0442\u044b"
            : lang.startsWith("uz")
                ? "Shaxta jurnali"
                : "Mine Journal",
    });

    const getTurnstileDeviceName = (row: Pick<EventRow, "device_name" | "device_host" | "device_id">): string => {
        if (row.device_host === "192.168.1.181") return "shaxta kirish";
        if (row.device_host === "192.168.1.180") return "shaxta chiqish";
        return row.device_name || String(row.device_id || "");
    };

    const getTurnstileDirection = (row: EventRow): { text: string; color: "INSIDE" | "OUTSIDE" } => {
        const isEntryByType = row.event_type === "TURNSTILE_IN" || row.event_type === "MINE_IN";
        const isExitByType = row.event_type === "TURNSTILE_OUT" || row.event_type === "MINE_OUT";
        const isEntry = isEntryByType || !isExitByType;
        return {
            text: isEntry ? t("dashboard.statusInside") : t("dashboard.statusOutside"),
            color: isEntry ? "INSIDE" : "OUTSIDE",
        };
    };

    const columns: GridColDef[] = [
        {
            field: "employee_no",
            headerName: t("events.col.employeeNo") || "Employee #",
            width: 160,
            hideable: false,
            valueGetter: (value) => formatEmployeeNo(value),
        },
        {
            field: "full_name",
            headerName: t("events.col.name") || "Name",
            width: 300,
            hideable: false,
            valueGetter: (_value, row) => {
                const parts = [row.last_name, row.first_name, row.patronymic].filter(Boolean);
                return parts.join(" ");
            },
        },
        {
            field: "event_ts",
            headerName: t("events.col.time"),
            width: 220,
            hideable: false,
            valueFormatter: (p) => {
                try {
                    return new Date(p as string).toLocaleString("en-GB");
                } catch {
                    return p as string;
                }
            },
        },
        {
            field: "device_name",
            headerName: t("events.col.deviceId") || "Device",
            width: 190,
            hideable: false,
            valueGetter: (_value, row) => getTurnstileDeviceName(row as EventRow),
        },
        {
            field: "status",
            headerName: t("events.col.status"),
            width: 130,
            hideable: false,
            renderCell: (p) => {
                const direction = getTurnstileDirection(p.row as EventRow);
                return <StatusPill status={direction.text} colorStatus={direction.color} />;
            },
        },
    ];

    const load = (
        page = paginationModel.page,
        pageSize = paginationModel.pageSize,
        sourceFilters: MainJournalFilters = appliedFilters,
    ) => {
        const params: EventFilters = {
            date_from: sourceFilters.date_from,
            date_to: sourceFilters.date_to,
            search: sourceFilters.search,
            status: "ACCEPTED",
            main_journal_only: true,
            offset: page * pageSize,
            limit: pageSize,
        };
        setLoading(true);
        fetchEventsPaged(params)
            .then((data) => {
                setRows(data.items);
                setRowCount(data.total);
            })
            .catch(() => {
                setRows([]);
                setRowCount(0);
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        load();
    }, [appliedFilters, paginationModel.page, paginationModel.pageSize]);

    useEffect(() => {
        const timer = window.setInterval(() => {
            load();
        }, 10000);
        return () => window.clearInterval(timer);
    }, [appliedFilters, paginationModel.page, paginationModel.pageSize]);

    return (
        <Box sx={{ height: "calc(100vh - 120px)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <Typography
                variant="h4"
                sx={{
                    mb: 3,
                    fontSize: "2.5rem",
                    fontWeight: 700,
                    flexShrink: 0,
                }}
            >
                <Box component="span" sx={pageTitleGradientSx}>
                    {mainJournalTitle}
                </Box>
            </Typography>
            <Box sx={{ mb: 4, display: "flex", gap: 2, alignItems: "center", flexWrap: "nowrap", flexShrink: 0 }}>
                <LocalizedDateInput
                    label={t("events.dateFrom")}
                    value={filters.date_from ? new Date(filters.date_from).toISOString().slice(0, 10) : ""}
                    onChange={(next) => setFilters((f) => ({ ...f, date_from: next ? new Date(next).toISOString() : undefined }))}
                />
                <LocalizedDateInput
                    label={t("events.dateTo")}
                    value={filters.date_to ? new Date(filters.date_to).toISOString().slice(0, 10) : ""}
                    onChange={(next) => setFilters((f) => ({ ...f, date_to: next ? new Date(next + "T23:59:59").toISOString() : undefined }))}
                />
                <TextField
                    label={t("events.search")}
                    placeholder={t("events.searchHint")}
                    sx={{ minWidth: 160 }}
                    onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
                />
                <Button
                    variant="contained"
                    onClick={() => {
                        const next = { ...paginationModel, page: 0 };
                        setAppliedFilters({ ...filters });
                        setPaginationModel(next);
                        load(0, next.pageSize, filters);
                    }}
                    sx={{ height: 40, minWidth: 100, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap" }}
                >
                    {t("events.apply")}
                </Button>
                <Button
                    variant="contained"
                    startIcon={<DownloadIcon />}
                    disabled
                    sx={{
                        height: 40,
                        borderRadius: "50px",
                        textTransform: "none",
                        fontWeight: "bold",
                        whiteSpace: "nowrap",
                        background: "linear-gradient(135deg, #06b6d4, #3b82f6)",
                        "&:hover": { background: "linear-gradient(135deg, #0891b2, #2563eb)" },
                    }}
                >
                    {t("events.exportCsv")}
                </Button>
                <Button
                    variant="contained"
                    startIcon={<PictureAsPdfIcon />}
                    disabled
                    sx={{
                        height: 40,
                        borderRadius: "50px",
                        textTransform: "none",
                        fontWeight: "bold",
                        whiteSpace: "nowrap",
                        background: "linear-gradient(135deg, #06b6d4, #3b82f6)",
                        "&:hover": { background: "linear-gradient(135deg, #0891b2, #2563eb)" },
                    }}
                >
                    {t("events.exportPdf")}
                </Button>
            </Box>
            <GlassCard sx={{ p: 0, flex: 1, width: "fit-content", minWidth: 1020, overflow: "hidden", "& .MuiDataGrid-root": { border: "none" } }}>
                <DataGrid
                    rows={rows}
                    columns={columns}
                    loading={loading}
                    rowCount={rowCount}
                    paginationMode="server"
                    pageSizeOptions={[25, 50, 100]}
                    paginationModel={paginationModel}
                    onPaginationModelChange={(model) => {
                        setPaginationModel(model);
                        load(model.page, model.pageSize);
                    }}
                    disableColumnSorting
                    disableColumnMenu
                    sx={{
                        height: "100%",
                        width: "100%",
                        "& .MuiDataGrid-columnHeaders": { bgcolor: tokens.bg.tableHeader },
                        "& .MuiDataGrid-row:nth-of-type(even)": { bgcolor: tokens.bg.tableRowAlt },
                        "& .MuiDataGrid-cell": { borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" },
                    }}
                />
            </GlassCard>
        </Box>
    );
}
